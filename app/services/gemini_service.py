import os
from dotenv import load_dotenv
from google import genai

# ================== CONFIGURACIÓN ==================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Falta la API KEY de Gemini")

client = genai.Client(api_key=GEMINI_API_KEY)

# ================== ENTRENAR MODELO ML ==================
modelo = None
try:
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor

    # Ruta relativa desde la ubicación del archivo actual
    excel_path = os.path.join(os.path.dirname(__file__), "..", "data", "preeclampsia_bd3.xlsx")
    excel_path = os.path.abspath(excel_path)

    print(f"Buscando archivo en: {excel_path}")
    print(f"¿Archivo existe?: {os.path.exists(excel_path)}")

    if os.path.exists(excel_path):
        print("Cargando datos del Excel...")
        df = pd.read_excel(excel_path)
        print(f"Columnas encontradas: {list(df.columns)}")
        print(f"Número de filas: {len(df)}")

        X = df[["age", "bmi", "htn", "diabetes", "fam_htn", "sysbp", "diabp"]]
        y = df["por_final"]  # Columna correcta según el archivo Excel
        modelo = RandomForestRegressor()
        modelo.fit(X, y)
        print("Modelo ML cargado exitosamente")
    else:
        print(f"Archivo de datos no encontrado en: {excel_path}, funcionando sin modelo ML")
except ImportError as ie:
    print(f"Error de importación: {ie}")
except Exception as e:
    print(f"Error cargando modelo ML: {e}, funcionando con reglas clínicas únicamente")
    import traceback
    traceback.print_exc()

# ================== FUNCIÓN DE CLASIFICACIÓN (REGLAS) ==================
def clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    demo = (edad < 18 or edad > 40 or imc >= 30)
    ant = (htn == 1 or diabetes == 1 or fam_htn == 1)
    presion_alta = (sysbp >= 140 or diabp >= 90)

    if presion_alta:
        return "ALTO"
    elif demo and ant:
        return "MEDIO"
    elif demo:
        return "BAJO"
    else:
        return "NINGUNO"

# ================== FUNCIÓN PRINCIPAL ==================
def generar_prediccion_gemini(edad, imc, htn, diabetes, fam_htn, sysbp, diabp):

    # 🔹 1. REGLAS CLÍNICAS
    riesgo_reglas = clasificar_riesgo(edad, imc, htn, diabetes, fam_htn, sysbp, diabp)

    # 🔹 2. MACHINE LEARNING 
    riesgo_ml = "NO DISPONIBLE"
    probabilidad = 0.0

    if modelo is not None:
        try:
            datos = [[edad, imc, htn, diabetes, fam_htn, sysbp, diabp]]
            pred_ml = modelo.predict(datos)[0]  # Probabilidad continua (0-1)

            # Convertir probabilidad a nivel de riesgo
            if pred_ml < 0.33:
                riesgo_ml = "BAJO"
            elif pred_ml < 0.66:
                riesgo_ml = "MEDIO"
            else:
                riesgo_ml = "ALTO"

            probabilidad = pred_ml
        except Exception as e:
            riesgo_ml = f"ERROR ML: {e}"
            probabilidad = 0.0

    # 🔹 3. GEMINI
    prompt = f"""
Eres un asistente médico especializado en preeclampsia.

Paciente con:
- Edad: {edad}
- IMC: {imc}
- Hipertensión previa: {int(htn)}
- Diabetes: {int(diabetes)}
- Antecedentes familiares HTN: {int(fam_htn)}
- Presión sistólica: {sysbp}
- Presión diastólica: {diabp}

Resultados del sistema:
- Clasificación por reglas clínicas: {riesgo_reglas}
- Clasificación por Machine Learning: {riesgo_ml}
- Probabilidad estimada por ML: {round(probabilidad*100,2)}%

Explica:
1. Interpretación clínica
2. Recomendaciones médicas
3. Posibles complicaciones
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
        "riesgo": riesgo_reglas,  # Para compatibilidad con la ruta existente
        "riesgo_reglas": riesgo_reglas,
        "riesgo_ml": riesgo_ml,
        "probabilidad_ml": round(probabilidad * 100, 2),
        "interpretacion": interpretacion,
    }