import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.shared.config.database import SessionLocal
from app.models.Consultas import Consulta
from app.models.Paciente import Paciente
from app.utils.generar_pdf import generar_html_reporte, generar_pdf
from app.routes.consulta_routes import prediccion_consulta

router = APIRouter(prefix="/reportes")

RUTA_REPORTES = "reportes"

# ✅ Crear carpeta si no existe (una sola vez)
if not os.path.exists(RUTA_REPORTES):
    os.makedirs(RUTA_REPORTES)


def obtener_ruta_pdf(consulta_id: int):
    return os.path.join(RUTA_REPORTES, f"reporte_{consulta_id}.pdf")


def _normalizar_riesgo_reporte(valor_riesgo) -> str:
    if not valor_riesgo:
        return "NINGUNO"

    if hasattr(valor_riesgo, "name"):
        return str(valor_riesgo.name).upper()

    texto = str(valor_riesgo).strip().upper()
    if texto.startswith("RIESGOENUM."):
        texto = texto.split(".", 1)[1]

    equivalencias = {
        "NINGUNO": "NINGUNO",
        "MEDIO": "MEDIO",
        "ALTO": "ALTO",
        "HOSPITALIZACION": "HOSPITALIZACION",
    }

    return equivalencias.get(texto, "NINGUNO")


def _obtener_contexto_reporte(consulta_id: int, db: Session):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")

    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if not consulta.interpretacion or consulta.score_total is None:
        try:
            prediccion_consulta(consulta_id, db)
            db.refresh(consulta)
        except Exception:
            consulta.interpretacion = "No se pudo generar interpretación automática."
            consulta.score_total = 0

    riesgo = _normalizar_riesgo_reporte(consulta.riesgo)
    score = consulta.score_total if consulta.score_total is not None else 0
    interpretacion = consulta.interpretacion or "Sin interpretación disponible"

    return consulta, paciente, riesgo, score, interpretacion


@router.get("/{consulta_id}/preview", response_class=HTMLResponse)
def vista_previa_reporte(consulta_id: int):
    db: Session = SessionLocal()

    try:
        consulta, paciente, riesgo, score, interpretacion = _obtener_contexto_reporte(consulta_id, db)

        html_content = generar_html_reporte(
            consulta=consulta,
            paciente=paciente,
            riesgo=riesgo,
            score=score,
            interpretacion=interpretacion,
        )

        return HTMLResponse(content=html_content)
    finally:
        db.close()


@router.get("/{consulta_id}")
def obtener_reporte(consulta_id: int):
    db: Session = SessionLocal()

    try:
        consulta, paciente, riesgo, score, interpretacion = _obtener_contexto_reporte(consulta_id, db)

        ruta_pdf = obtener_ruta_pdf(consulta_id)

        try:
            generar_pdf(
                consulta=consulta,
                paciente=paciente,
                ruta_pdf=ruta_pdf,
                riesgo=riesgo,
                score=score,
                interpretacion=interpretacion
            )
        except Exception as e:
            print("ERROR GENERANDO PDF:", e)
            raise HTTPException(status_code=500, detail="Error generando PDF")

        return FileResponse(
            ruta_pdf,
            media_type="application/pdf",
            filename=f"reporte_{consulta_id}.pdf",
            content_disposition_type="inline",
        )
    finally:
        db.close()