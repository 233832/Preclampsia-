import os
from dotenv import load_dotenv
from google import genai

# ================== CONFIGURACIÓN ==================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Falta la API KEY de Gemini")

client = genai.Client(api_key=GEMINI_API_KEY)

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

    if htn == 1 or diabetes == 1:
        return "ALTO"

    pesos = calcular_pesos(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    score_mod = (
        pesos["age"] +
        pesos["bmi"] +
        pesos["sysbp"] +
        pesos["diabp"] +
        pesos["fam"]
    )

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

# ================== ENTRENAR MODELO ML ==================
modelo = None
scaler = None

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    excel_path = os.path.join(os.path.dirname(__file__), "..", "data", "preeclampsia_bd4.xlsx")
    excel_path = os.path.abspath(excel_path)

    print(f"Buscando archivo en: {excel_path}")

    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)

        print("Columnas encontradas:", list(df.columns))

        X = df[["age", "bmi", "htn", "diabetes", "fam_htn", "sysbp", "diabp"]]
        y = df["riesgo_clase"]

        # ESCALADO
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # MODELO MEJORADO
        modelo = RandomForestClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_split=5,
            random_state=42
        )

        modelo.fit(X_scaled, y)

        print("Modelo ML cargado exitosamente")

    else:
        print("Archivo no encontrado, usando solo reglas clínicas")

except Exception as e:
    print(f"Error cargando modelo ML: {e}")

# ================== FUNCIÓN PRINCIPAL ==================
def generar_prediccion_gemini(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    # CONVERSIÓN CLAVE
    htn = int(htn)
    diabetes = int(diabetes)
    fam_htn = int(fam_htn)

    # Reglas clínicas
    riesgo_reglas = clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    # Score
    score_total = calcular_score_total(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    # ML
    riesgo_ml = "NO DISPONIBLE"
    probabilidad = 0.0

    if modelo is not None and scaler is not None:
        try:
            datos = [[edad, imc, htn, diabetes, fam_htn, sysbp, diabp]]

            # ESCALAR TAMBIÉN EN PREDICCIÓN
            datos_scaled = scaler.transform(datos)

            pred_ml = modelo.predict(datos_scaled)[0]

            riesgos = ["BAJO", "MEDIO", "ALTO"]
            riesgo_ml = riesgos[pred_ml]

            proba = modelo.predict_proba(datos_scaled)[0]
            probabilidad = max(proba)

        except Exception as e:
            riesgo_ml = f"ERROR ML: {e}"

    # PROMPT 
    prompt = f"""
Eres un asistente médico especializado en preeclampsia.

REGLAS OBLIGATORIAS:
- No generar contradicciones clínicas.
- Si presión diastólica >= 90, considerar hipertensión actual.
- Si la confianza del ML < 60%, priorizar reglas clínicas.

Paciente:
- Edad: {edad}
- IMC: {imc}
- Hipertensión: {htn}
- Diabetes: {diabetes}
- Antecedente familiar: {fam_htn}
- Presión sistólica: {sysbp}
- Presión diastólica: {diabp}

Resultados:
- Riesgo por reglas: {riesgo_reglas}
- Riesgo por ML: {riesgo_ml}
- Score total: {round(score_total,2)}
- Confianza ML: {round(probabilidad*100,2)}%

Explica:
1. Interpretación clínica clara
2. Diferencia entre reglas y ML
3. Riesgo final justificado
4. Recomendaciones médicas
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        interpretacion = response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        interpretacion = f"Error con Gemini: {e}"

    return {
        "riesgo": riesgo_reglas,
        "riesgo_ml": riesgo_ml,
        "score_total": round(score_total, 2),
        "confianza_ml": round(probabilidad * 100, 2),
        "interpretacion": interpretacion,
    }