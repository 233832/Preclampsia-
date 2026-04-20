from fastapi import APIRouter, Depends
import unicodedata
from app.services.medicacion_service import obtener_medicacion_por_riesgo

router = APIRouter()


def normalizar_riesgo(riesgo: str) -> str:
    texto = unicodedata.normalize("NFKD", riesgo)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().upper().replace("-", "_").replace(" ", "_")

    alias = {
        "BAJO": "NINGUNO",
        "MODERADO": "MEDIO",
        "HOSPITALIZACION_URGENTE": "HOSPITALIZACION",
        "HOSPITALIZACION_INMEDIATA": "HOSPITALIZACION",
        "URGENTE": "HOSPITALIZACION",
    }

    return alias.get(texto, texto)


@router.get("/medicacion/{riesgo}")
@router.get("/medicamentos/{riesgo}")
def get_medicacion(riesgo: str):
    riesgo_normalizado = normalizar_riesgo(riesgo)
    data = obtener_medicacion_por_riesgo(riesgo_normalizado)

    if not data:
        return {
            "message": "Riesgo no valido. Usa: NINGUNO, MEDIO, ALTO, HOSPITALIZACION"
        }

    return data