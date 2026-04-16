import os
import unicodedata
from dotenv import load_dotenv

# ================== GEMINI ==================
try:
    from google import genai
except Exception:
    genai = None

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        client = None

GEMINI_DISPONIBLE = client is not None


# ================== FACTORES ==================
def calcular_factores(datos):

    factores = []

    edad = datos["age"]
    imc = datos["bmi"]
    sysbp = datos["sysbp"]
    diabp = datos["diabp"]
    pam = datos["presion_art_media"]

    htn = datos["htn"]
    diabetes = datos["diabetes"]
    fam_htn = datos["fam_htn"]
    fam_cardio = datos["fam_cardiopatia"]
    renal = datos["enf_renal_cronica"]
    multiple = datos["embarazo_multiple"]
    muerte = datos["muerte_fetal"]
    rcf = datos["restriccion_fetal"]

    # 🔹 FACTORES (TUS PESOS)

    if edad >= 40:
        factores.append(("edad", 1.82))

    if imc >= 30:
        factores.append(("imc", 2.47))

    if fam_htn == 1:
        factores.append(("fam_htn", 3))

    if fam_cardio == 1:
        factores.append(("fam_cardio", 3))

    if diabetes == 1:
        factores.append(("diabetes", 3.6))

    if htn == 1:
        factores.append(("htn", 3.6))

    if sysbp >= 140:
        factores.append(("ps", 2.4))

    if diabp >= 90:
        factores.append(("pd", 1.4))

    if renal == 1:
        factores.append(("renal", 3.6))

    if multiple == 1:
        factores.append(("multiple", 2.9))

    # 🔴 CRISIS HIPERTENSIVA
    if sysbp >= 160 or diabp >= 110:
        factores.append(("crisis_htn", 5.4))

    # 🔹 CUALITATIVOS (no suman)
    if muerte == 1:
        factores.append(("muerte_fetal", 0))

    if rcf == 1:
        factores.append(("rcf", 0))

    return factores


# ================== CLASIFICACIÓN ==================
def clasificar_riesgo(datos):

    sysbp = datos["sysbp"]
    diabp = datos["diabp"]
    pam = datos["presion_art_media"]

    # 🚨 CRITERIO ABSOLUTO
    if sysbp >= 160 or diabp >= 110 or pam >= 110:
        return "HOSPITALIZACION", 34.59

    factores = calcular_factores(datos)
    score = sum([peso for _, peso in factores])

    # 🔹 ESCALA BASADA EN TU TOTAL
    if score == 0:
        return "NINGUNO", 0

    if score < 13.7:
        return "MEDIO", round(score, 2)

    if score < 29.19:
        return "ALTO", round(score, 2)

    return "HOSPITALIZACION", round(score, 2)


# ================== FALLBACK ==================
def generar_interpretacion_fallback(riesgo, score, sysbp, diabp):

    if riesgo == "HOSPITALIZACION":
        return f"Riesgo crítico. Presión {sysbp}/{diabp} mmHg. Hospitalización inmediata."

    if riesgo == "ALTO":
        return f"Riesgo alto (score {score}). Presión {sysbp}/{diabp}. Atención urgente."

    if riesgo == "MEDIO":
        return f"Riesgo moderado (score {score}). Monitoreo recomendado."

    return "Sin factores de riesgo."


# ================== GEMINI ==================
def generar_interpretacion_clinica_limpia(
    edad, imc, htn, diabetes, fam_htn, sysbp, diabp,
    riesgo_final, score_total
):

    if not GEMINI_DISPONIBLE:
        return generar_interpretacion_fallback(
            riesgo_final, score_total, sysbp, diabp
        )

    prompt = f"""
Actúa como médico especialista en preeclampsia.

Paciente:
Edad: {edad}
IMC: {imc}
HTA: {htn}
Diabetes: {diabetes}
Antecedente familiar: {fam_htn}
Presión: {sysbp}/{diabp}

Resultado:
Riesgo: {riesgo_final}
Score: {score_total}

Máximo 3 líneas.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return response.text.strip()
    except:
        return generar_interpretacion_fallback(
            riesgo_final, score_total, sysbp, diabp
        )


# ================== ML ==================
modelo = None
scaler = None

FEATURE_COLUMNS = [
    "age", "bmi", "sysbp", "diabp", "presion_art_media",
    "htn", "diabetes", "fam_htn", "fam_cardiopatia",
    "enf_renal_cronica", "embarazo_multiple",
    "muerte_fetal", "restriccion_fetal",
]

RISK_CLASS_TO_INT = {
    "NINGUNO": 0,
    "MEDIO": 1,
    "ALTO": 2,
    "HOSPITALIZACION": 3,
}

RISK_INT_TO_TEXT = {
    0: "NINGUNO",
    1: "MEDIO",
    2: "ALTO",
    3: "HOSPITALIZACION",
}


def _normalizar_etiqueta_riesgo(valor) -> str:
    texto = str(valor or "").strip()
    texto = "".join(
        char for char in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(char)
    )
    texto = texto.upper()

    equivalencias = {
        "BAJO": "MEDIO",
        "MODERADO": "MEDIO",
        "SEVERO": "ALTO",
        "NINGUNA": "NINGUNO",
        "HOSPITALIZACION URGENTE": "HOSPITALIZACION",
        "HOSPITALIZACION INMEDIATA": "HOSPITALIZACION",
        "URGENTE": "HOSPITALIZACION",
    }
    return equivalencias.get(texto, texto)


def _riesgo_texto_a_int(serie):
    y_texto = serie.astype(str).map(_normalizar_etiqueta_riesgo)
    return y_texto.map(RISK_CLASS_TO_INT)


def cargar_modelo_ml(force=False) -> bool:
    global modelo, scaler

    if not force and modelo is not None and scaler is not None:
        return True

    modelo = None
    scaler = None

    try:
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler

        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "preeclampsia_bd6.xlsx"
        )
        path = os.path.abspath(path)

        if not os.path.exists(path):
            return False

        df = pd.read_excel(path)
        if not set(FEATURE_COLUMNS).issubset(df.columns):
            return False

        df_model = df[FEATURE_COLUMNS].copy()

        for column in FEATURE_COLUMNS:
            df_model[column] = pd.to_numeric(df_model[column], errors="coerce")

        y_num = None

        if "riesgo_clase" in df.columns:
            y_num = pd.to_numeric(df["riesgo_clase"], errors="coerce")
            if y_num.isna().all():
                y_num = None

        if y_num is None and "Risk" in df.columns:
            y_num = _riesgo_texto_a_int(df["Risk"])

        if y_num is None and "riesgo" in df.columns:
            y_num = _riesgo_texto_a_int(df["riesgo"])

        if y_num is None:
            return False

        df_model["riesgo_clase"] = y_num
        required_columns = FEATURE_COLUMNS + ["riesgo_clase"]

        df_model = df_model.dropna(subset=required_columns)
        df_model = df_model[df_model["riesgo_clase"].isin(RISK_CLASS_TO_INT.values())]

        if df_model.empty:
            return False

        X = df_model[FEATURE_COLUMNS]
        y = df_model["riesgo_clase"].astype(int)

        scaler_local = StandardScaler()
        X_scaled = scaler_local.fit_transform(X)

        modelo_local = RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            random_state=42
        )
        modelo_local.fit(X_scaled, y)

        scaler = scaler_local
        modelo = modelo_local
        return True

    except Exception:
        modelo = None
        scaler = None
        return False


def predecir_riesgo_ml(datos) -> tuple[str, float]:
    if modelo is None or scaler is None:
        return "NO DISPONIBLE", 0.0

    try:
        X_input = [[
            datos["age"],
            datos["bmi"],
            datos["sysbp"],
            datos["diabp"],
            datos["presion_art_media"],
            datos["htn"],
            datos["diabetes"],
            datos["fam_htn"],
            datos["fam_cardiopatia"],
            datos["enf_renal_cronica"],
            datos["embarazo_multiple"],
            datos["muerte_fetal"],
            datos["restriccion_fetal"],
        ]]

        X_scaled = scaler.transform(X_input)
        pred = modelo.predict(X_scaled)[0]
        riesgo_ml = RISK_INT_TO_TEXT.get(int(pred), "NO DISPONIBLE")
        confianza = max(modelo.predict_proba(X_scaled)[0]) * 100
        return riesgo_ml, round(confianza, 2)

    except Exception:
        return "NO DISPONIBLE", 0.0


# ================== FUNCIÓN PRINCIPAL ==================
def generar_prediccion_gemini(datos):

    # 🔹 REGLAS CLÍNICAS
    riesgo_reglas, score = clasificar_riesgo(datos)

    riesgo_ml, confianza = predecir_riesgo_ml(datos)

    # 🔥 REGLA DE ORO
    if riesgo_reglas == "HOSPITALIZACION":
        riesgo_final = "HOSPITALIZACION"
    else:
        riesgo_final = riesgo_reglas

    interpretacion = generar_interpretacion_clinica_limpia(
        datos["age"], datos["bmi"], datos["htn"], datos["diabetes"],
        datos["fam_htn"], datos["sysbp"], datos["diabp"],
        riesgo_final, score
    )

    return {
        "riesgo": riesgo_final,
        "riesgo_ml": riesgo_ml,
        "score_total": score,
        "confianza_ml": confianza,
        "interpretacion": interpretacion,
    }