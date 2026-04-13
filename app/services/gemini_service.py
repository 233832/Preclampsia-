import os
from dotenv import load_dotenv

try:
    from google import genai
except Exception:
    genai = None

# ================== CONFIGURACIÓN ==================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

client = None

if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        print(f"Gemini deshabilitado: {exc}")
elif not GEMINI_API_KEY:
    print("Gemini deshabilitado: falta GEMINI_API_KEY en entorno")
else:
    print("Gemini deshabilitado: libreria google-genai no disponible")

GEMINI_DISPONIBLE = client is not None

# ================== FUNCIONES DE PESOS ==================
def calcular_pesos(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    peso_age = 1.82 if (edad >= 40 or edad < 18) else 0
    peso_bmi = 2.47 if imc >= 30 else 0
    peso_sysbp = 2.4 if sysbp >= 140 else 0
    peso_diabp = 1.4 if diabp >= 90 else 0
    peso_fam = 3 if fam_htn == 1 else 0
    peso_htn = 3.6 if htn == 1 else 0
    peso_diabetes = 3.6 if diabetes == 1 else 0

    return {
        "age": peso_age,
        "bmi": peso_bmi,
        "sysbp": peso_sysbp,
        "diabp": peso_diabp,
        "fam": peso_fam,
        "htn": peso_htn,
        "diabetes": peso_diabetes
    }

# ================== CLASIFICACIÓN ==================
def clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    pesos = calcular_pesos(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)
    score_total = sum(pesos.values())

    score_mod = (
        pesos["age"] +
        pesos["bmi"] +
        pesos["sysbp"] +
        pesos["diabp"] +
        pesos["fam"]
    )

    if score_total == 0:
        return "NINGUNO"

    if htn == 1 or diabetes == 1:
        return "ALTO"

    if score_mod > 11.09:
        return "ALTO"
    elif score_mod >= 4:
        return "MEDIO"
    else:
        return "BAJO"

# ================== SCORE TOTAL ==================
def calcular_score_total(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):
    pesos = calcular_pesos(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)
    return sum(pesos.values())


def generar_interpretacion_fallback(riesgo_final, score_total, sysbp, diabp):
    riesgo = str(riesgo_final).upper()
    score_texto = round(score_total, 2)

    if riesgo == "ALTO":
        return (
            f"Riesgo alto de preeclampsia (score {score_texto}).\n"
            f"Presion actual: {sysbp}/{diabp} mmHg.\n"
            "Se recomienda valoracion obstetrica prioritaria y vigilancia estrecha."
        )

    if riesgo == "MEDIO":
        return (
            f"Riesgo moderado de preeclampsia (score {score_texto}).\n"
            f"Presion actual: {sysbp}/{diabp} mmHg.\n"
            "Sugerir control prenatal frecuente y monitoreo de sintomas de alarma."
        )

    if riesgo == "BAJO":
        return (
            f"Riesgo bajo de preeclampsia (score {score_texto}).\n"
            "Mantener seguimiento prenatal habitual y control periodico de presion arterial."
        )

    return "Sin riesgo clinico evidente de preeclampsia en esta evaluacion."

# ================== MODELO ML ==================
modelo = None
scaler = None

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    excel_path = os.path.join(os.path.dirname(__file__), "..", "data", "preeclampsia_bd4.xlsx")
    excel_path = os.path.abspath(excel_path)

    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)

        X = df[["age", "bmi", "htn", "diabetes", "fam_htn", "sysbp", "diabp"]]
        y = df["riesgo_clase"]

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        modelo = RandomForestClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_split=5,
            random_state=42
        )

        modelo.fit(X_scaled, y)

        print("Modelo ML cargado correctamente")

    else:
        print("Archivo no encontrado, usando solo reglas")

except Exception as e:
    print(f"Error ML: {e}")

# ================== NUEVA FUNCIÓN IA LIMPIA ==================
def generar_interpretacion_clinica_limpia(
    edad, imc, htn, diabetes, fam_htn, sysbp, diabp,
    riesgo_final, score_total
):

    if not GEMINI_DISPONIBLE:
        return generar_interpretacion_fallback(riesgo_final, score_total, sysbp, diabp)

    prompt = f"""
Actúa como un médico especialista en preeclampsia.

Genera una interpretación clínica breve, clara y profesional.

Reglas:
- Máximo 5 líneas
- Sin símbolos (#, **, etc.)
- No mencionar IA ni modelos
- Lenguaje clínico simple

Paciente:
Edad: {edad}
IMC: {imc}
Hipertensión: {htn}
Diabetes: {diabetes}
Antecedente familiar: {fam_htn}
Presión: {sysbp}/{diabp}

Resultado:
Riesgo: {riesgo_final}
Score: {round(score_total,2)}

Redacta directamente la interpretación.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            generation_config={
                "max_output_tokens": 150,
                "temperature": 0.4
            }
        )
        if response and getattr(response, "text", None):
            return response.text.strip()
        return generar_interpretacion_fallback(riesgo_final, score_total, sysbp, diabp)
    except Exception as e:
        print(f"Gemini no disponible en tiempo de ejecucion: {e}")
        return generar_interpretacion_fallback(riesgo_final, score_total, sysbp, diabp)

# ================== FUNCIÓN PRINCIPAL ==================
def generar_prediccion_gemini(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    htn = int(htn)
    diabetes = int(diabetes)
    fam_htn = int(fam_htn)

    # 🔹 Reglas
    riesgo_reglas = clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    # 🔹 Score
    score_total = calcular_score_total(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    # 🔹 ML
    riesgo_ml = "NO DISPONIBLE"
    probabilidad = 0.0

    if score_total == 0:
        riesgo_reglas = "NINGUNO"
        riesgo_ml = "NINGUNO"
        probabilidad = 1.0

    else:
        if modelo is not None and scaler is not None:
            try:
                datos = [[edad, imc, htn, diabetes, fam_htn, sysbp, diabp]]
                datos_scaled = scaler.transform(datos)

                pred_ml = modelo.predict(datos_scaled)[0]
                riesgos = ["BAJO", "MEDIO", "ALTO"]
                riesgo_ml = riesgos[pred_ml]

                proba = modelo.predict_proba(datos_scaled)[0]
                probabilidad = max(proba)

            except Exception as e:
                riesgo_ml = f"ERROR ML: {e}"

    # 🔥 INTERPRETACIÓN LIMPIA
    interpretacion = generar_interpretacion_clinica_limpia(
        edad, imc, htn, diabetes, fam_htn, sysbp, diabp,
        riesgo_final=riesgo_reglas,
        score_total=score_total
    )

    return {
        "riesgo": riesgo_reglas,
        "riesgo_ml": riesgo_ml,
        "score_total": round(score_total, 2),
        "confianza_ml": round(probabilidad * 100, 2),
        "interpretacion": interpretacion,
    }