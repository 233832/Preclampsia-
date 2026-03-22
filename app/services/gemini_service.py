import os
from dotenv import load_dotenv
from google import genai

# ================== CONFIGURACIÓN ==================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Falta la API KEY de Gemini")

client = genai.Client(api_key=GEMINI_API_KEY)

# ================== FUNCIÓN DE CLASIFICACIÓN ==================
def clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):
    # Demográficos
    riesgo_demo = (edad < 18 or edad > 40 or imc > 30)

    # Antecedentes
    riesgo_antecedentes = bool(htn) or bool(diabetes) or bool(fam_htn)

    # Presión arterial
    riesgo_presion = (sysbp >= 140 or diabp >= 90)

    if riesgo_demo and not riesgo_antecedentes and not riesgo_presion:
        return "RIESGO BAJO"
    if riesgo_demo and riesgo_antecedentes and not riesgo_presion:
        return "RIESGO MEDIO"
    if riesgo_presion and riesgo_antecedentes and riesgo_demo:
        return "RIESGO ALTO"

    return "SIN RIESGO CLARO"


def generar_prediccion_gemini(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):
    riesgo = clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    prompt = f"""
Eres un asistente médico especializado en preeclampsia.

Paciente embarazada con:
- Edad: {edad}
- IMC: {imc}
- Hipertensión previa: {int(htn)}
- Diabetes: {int(diabetes)}
- Antecedentes familiares de hipertensión: {int(fam_htn)}
- Presión sistólica: {sysbp}
- Presión diastólica: {diabp}

Clasificación de riesgo: {riesgo}

Por favor, explica:
1. Por qué está en ese nivel de riesgo
2. Qué significa clínicamente
3. Recomendaciones de manejo inicial y derivación
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        interpretacion = response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        interpretacion = f"Error generando predicción con Gemini: {e}"

    return {
        "riesgo": riesgo,
        "interpretacion": interpretacion,
    }
