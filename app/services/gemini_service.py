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


# ================== UMBRALES CLINICOS ==================
SCORE_TOTAL_MAX = 33.19
SCORE_MEDIO_MAX = 13.7

PRESION_SISTOLICA_MEDIO = 140
PRESION_DIASTOLICA_MEDIO_1 = 90
PRESION_ARTERIAL_MEDIA_MEDIO = 95
PRESION_SISTOLICA_HOSP = 160
PRESION_DIASTOLICA_HOSP = 110

FACTORES_ALTO_AUTO = (
    "diabetes",
    "htn",
    "enf_renal_cronica",
    "embarazo_multiple",
)


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

    if sysbp >= PRESION_SISTOLICA_MEDIO:
        factores.append(("ps", 2.4))

    if diabp >= PRESION_DIASTOLICA_MEDIO_1:
        factores.append(("pd_1", 1.4))

    # PAM medio es criterio clinico, sin peso adicional en score.
    if pam > PRESION_ARTERIAL_MEDIA_MEDIO:
        factores.append(("pam_medio", 0))

    if renal == 1:
        factores.append(("renal", 3.6))

    if multiple == 1:
        factores.append(("multiple", 2.9))

    # 🔴 CRISIS HIPERTENSIVA
    if sysbp >= PRESION_SISTOLICA_HOSP or diabp >= PRESION_DIASTOLICA_HOSP:
        factores.append(("crisis_htn", 5.4))

    # 🔹 CUALITATIVOS (no suman)
    if muerte == 1:
        factores.append(("muerte_fetal", 0))

    if rcf == 1:
        factores.append(("rcf", 0))

    return factores


def _hay_factor_alto_positivo(datos) -> bool:
    for clave in FACTORES_ALTO_AUTO:
        try:
            if int(datos.get(clave, 0)) == 1:
                return True
        except Exception:
            continue
    return False


def _pam_en_rango_medio(pam: float) -> bool:
    return pam > PRESION_ARTERIAL_MEDIA_MEDIO


# ================== CLASIFICACIÓN ==================
def clasificar_riesgo(datos):

    sysbp = float(datos["sysbp"])
    diabp = float(datos["diabp"])
    pam = float(datos["presion_art_media"])

    crisis_hipertensiva = (
        sysbp >= PRESION_SISTOLICA_HOSP or diabp >= PRESION_DIASTOLICA_HOSP
    )

    factores = calcular_factores(datos)
    score = round(sum(peso for _, peso in factores), 2)

    # Hospitalizacion automatica por crisis hipertensiva.
    if crisis_hipertensiva:
        return "HOSPITALIZACION", SCORE_TOTAL_MAX

    # Hospitalizacion por score maximo acumulado.
    if score >= SCORE_TOTAL_MAX:
        return "HOSPITALIZACION", SCORE_TOTAL_MAX

    # Alto automatico cuando una variable de la seccion ALTO es positiva.
    if _hay_factor_alto_positivo(datos):
        return "ALTO", score

    if score > SCORE_MEDIO_MAX:
        return "ALTO", score

    if 1 <= score <= SCORE_MEDIO_MAX:
        return "MEDIO", score

    if _pam_en_rango_medio(pam):
        return "MEDIO", score

    return "NINGUNO", 0


def _fila_a_datos_prediccion(fila: dict) -> dict:
    return {
        "age": float(fila["age"]),
        "bmi": float(fila["bmi"]),
        "sysbp": float(fila["sysbp"]),
        "diabp": float(fila["diabp"]),
        "presion_art_media": float(fila["presion_art_media"]),
        "htn": int(round(float(fila["htn"]))),
        "diabetes": int(round(float(fila["diabetes"]))),
        "fam_htn": int(round(float(fila["fam_htn"]))),
        "fam_cardiopatia": int(round(float(fila["fam_cardiopatia"]))),
        "enf_renal_cronica": int(round(float(fila["enf_renal_cronica"]))),
        "embarazo_multiple": int(round(float(fila["embarazo_multiple"]))),
        "muerte_fetal": int(round(float(fila["muerte_fetal"]))),
        "restriccion_fetal": int(round(float(fila["restriccion_fetal"]))),
    }


def _etiqueta_regla_a_int(fila: dict) -> int | None:
    try:
        datos = _fila_a_datos_prediccion(fila)
        riesgo, _ = clasificar_riesgo(datos)
        return RISK_CLASS_TO_INT.get(riesgo)
    except Exception:
        return None


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

        df_model = df_model.dropna(subset=FEATURE_COLUMNS)
        if df_model.empty:
            return False

        # Entrenamiento alineado con reglas clinicas actuales.
        df_model["riesgo_clase"] = df_model.apply(_etiqueta_regla_a_int, axis=1)
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
            n_estimators=500,
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
    riesgo_reglas, _ = clasificar_riesgo(datos)

    if modelo is None or scaler is None:
        return riesgo_reglas, 0.0

    try:
        import pandas as pd

        X_input = pd.DataFrame([
            {
                "age": datos["age"],
                "bmi": datos["bmi"],
                "sysbp": datos["sysbp"],
                "diabp": datos["diabp"],
                "presion_art_media": datos["presion_art_media"],
                "htn": datos["htn"],
                "diabetes": datos["diabetes"],
                "fam_htn": datos["fam_htn"],
                "fam_cardiopatia": datos["fam_cardiopatia"],
                "enf_renal_cronica": datos["enf_renal_cronica"],
                "embarazo_multiple": datos["embarazo_multiple"],
                "muerte_fetal": datos["muerte_fetal"],
                "restriccion_fetal": datos["restriccion_fetal"],
            }
        ], columns=FEATURE_COLUMNS)

        X_scaled = scaler.transform(X_input)
        pred = modelo.predict(X_scaled)[0]
        riesgo_ml = RISK_INT_TO_TEXT.get(int(pred), riesgo_reglas)
        confianza = float(max(modelo.predict_proba(X_scaled)[0]) * 100)

        # Se fuerza consistencia con reglas clinicas para evitar discrepancias.
        if riesgo_ml != riesgo_reglas:
            return riesgo_reglas, round(confianza, 2)

        return riesgo_ml, round(confianza, 2)

    except Exception:
        return riesgo_reglas, 0.0


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