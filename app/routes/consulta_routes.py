from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Consultas import Consulta, RiesgoEnum
from app.models.Paciente import Paciente
from app.models.ExpedienteClinico import ExpedienteClinico
from app.schemas.consulta_schema import ConsultaCreate, ConsultaResponse
from app.services.gemini_service import (
    generar_prediccion_gemini,
    clasificar_riesgo,
    predecir_riesgo_ml,
)
from app.services.notificacion_service import crear_notificacion
from app.models.Notificaciones import TipoNotificacionEnum
from fastapi.responses import FileResponse
import base64
import os
import unicodedata

consulta_router = APIRouter()


def _bool_a_int(valor: bool) -> int:
    return 1 if bool(valor) else 0


def _calcular_pam(sistolica: float, diastolica: float) -> float:
    return (sistolica + 2 * diastolica) / 3


def _armar_datos_prediccion(consulta, paciente: Paciente) -> dict:
    sistolica = float(getattr(consulta, "presion_sistolica", 0) or 0)
    diastolica = float(getattr(consulta, "presion_diastolica", 0) or 0)

    pam_existente = getattr(consulta, "pam", None)
    try:
        pam = float(pam_existente) if pam_existente is not None else 0.0
    except Exception:
        pam = 0.0

    if pam <= 0:
        pam = _calcular_pam(sistolica, diastolica)

    return {
        "age": float(getattr(consulta, "edad_madre", 0) or 0),
        "bmi": float(getattr(consulta, "imc", 0) or 0),
        "sysbp": sistolica,
        "diabp": diastolica,
        "presion_art_media": pam,
        "htn": _bool_a_int(getattr(paciente, "hipertension_previa", False)),
        "diabetes": _bool_a_int(getattr(paciente, "diabetes", False)),
        "fam_htn": _bool_a_int(getattr(paciente, "antecedentes_familia_hipertension", False)),
        "fam_cardiopatia": _bool_a_int(getattr(paciente, "fam_cardiopatia", False)),
        "enf_renal_cronica": _bool_a_int(getattr(paciente, "enf_renal_cronica", False)),
        "embarazo_multiple": _bool_a_int(getattr(paciente, "embarazo_multiple", False)),
        "antecedente_preeclampsia_embarazo_previo": _bool_a_int(
            getattr(paciente, "antecedente_preeclampsia_embarazo_previo", False)
        ),
        "muerte_fetal": _bool_a_int(getattr(paciente, "muerte_fetal", False)),
        "restriccion_fetal": _bool_a_int(getattr(paciente, "restriccion_fetal", False)),
    }


def _calcular_resultados_consulta(consulta, paciente: Paciente) -> dict:
    datos_prediccion = _armar_datos_prediccion(consulta, paciente)

    riesgo_str, score_total = clasificar_riesgo(datos_prediccion)
    riesgo_enum = normalizar_riesgo_enum(riesgo_str)

    riesgo_ml_modelo, confianza_ml = predecir_riesgo_ml(datos_prediccion)
    try:
        confianza_ml_float = float(confianza_ml)
    except Exception:
        confianza_ml_float = 0.0

    return {
        "pam": float(datos_prediccion["presion_art_media"]),
        "riesgo_enum": riesgo_enum,
        "score_total": score_total,
        "riesgo_ml": riesgo_enum.name,
        "riesgo_ml_modelo": str(riesgo_ml_modelo),
        "confianza_ml": confianza_ml_float,
    }


def _adjuntar_resultados_a_consulta(consulta: Consulta, resultados: dict) -> None:
    consulta.pam = resultados["pam"]
    consulta.riesgo = resultados["riesgo_enum"]
    consulta.score_total = resultados["score_total"]
    consulta.riesgo_ml = resultados["riesgo_ml"]
    consulta.riesgo_ml_modelo = resultados["riesgo_ml_modelo"]
    consulta.confianza_ml = resultados["confianza_ml"]


def normalizar_riesgo_enum(valor_riesgo) -> RiesgoEnum:
    if isinstance(valor_riesgo, RiesgoEnum):
        return valor_riesgo

    texto = str(valor_riesgo or "").strip()
    if not texto:
        return RiesgoEnum.NINGUNO

    texto_sin_acentos = "".join(
        char for char in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(char)
    )
    clave = texto_sin_acentos.upper()

    if clave.startswith("RIESGOENUM."):
        clave = clave.split(".", 1)[1]

    equivalencias = {
        "NINGUNO": "NINGUNO",
        "MEDIO": "MEDIO",
        "ALTO": "ALTO",
        "HOSPITALIZACION": "HOSPITALIZACION",
    }

    if clave in equivalencias:
        return RiesgoEnum[equivalencias[clave]]

    for riesgo_enum in RiesgoEnum:
        valor_sin_acentos = "".join(
            char for char in unicodedata.normalize("NFKD", riesgo_enum.value)
            if not unicodedata.combining(char)
        )
        if valor_sin_acentos.upper() == clave:
            return riesgo_enum

    return RiesgoEnum.NINGUNO


def get_weasyprint_html():
    try:
        from weasyprint import HTML
        return HTML, None
    except Exception as exc:
        return None, exc


def generar_pdf_reportlab_fallback(
    file_path: str,
    consulta: Consulta,
    paciente: Paciente,
    fecha_texto: str,
    riesgo: str,
    score: int,
    interpretacion: str,
    logo_path: str,
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(file_path, pagesize=A4)
    _, height = A4

    if os.path.exists(logo_path):
        try:
            pdf.drawImage(
                logo_path,
                40,
                height - 90,
                width=70,
                height=40,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(130, height - 65, "Reporte de Evaluacion de Preeclampsia")

    y = height - 125

    def line(label: str, value) -> None:
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(40, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(200, y, str(value))
        y -= 18

    line("ID Consulta", consulta.id)
    line("Fecha", fecha_texto)
    line("Paciente", paciente.nombre)
    line("Edad", consulta.edad_madre)
    line("IMC", consulta.imc)
    line("Score", score)

    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Riesgo")
    y -= 18

    riesgo_label = str(riesgo).upper()

    color_map = {
        "NINGUNO": "#95A5A6",
        "HOSPITALIZACION": "#2980B9",
        "MEDIO": "#E67E22",
        "ALTO": "#C0392B",
    }
    riesgo_color = HexColor(color_map.get(riesgo_label, "#7F8C8D"))
    pdf.setFillColor(riesgo_color)
    pdf.roundRect(40, y - 6, 180, 24, 6, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, y + 2, riesgo_label)
    pdf.setFillColorRGB(0, 0, 0)
    y -= 38

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Interpretacion clinica")
    y -= 16
    pdf.setFont("Helvetica", 10)

    texto = str(interpretacion or "Sin interpretacion disponible")
    for raw_line in texto.splitlines() or [texto]:
        text_line = raw_line.strip()
        if not text_line:
            continue
        while len(text_line) > 110:
            cut = text_line.rfind(" ", 0, 110)
            if cut == -1:
                cut = 110
            pdf.drawString(40, y, text_line[:cut])
            y -= 14
            text_line = text_line[cut:].strip()
            if y < 80:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)
        if text_line:
            pdf.drawString(40, y, text_line)
            y -= 14
            if y < 80:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)

    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(40, 30, "Generado automaticamente por el sistema biomedico")
    pdf.save()

@consulta_router.post("/consultas/", response_model=ConsultaResponse, status_code=status.HTTP_201_CREATED)
def create_consulta(consulta: ConsultaCreate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")

    if not db.query(ExpedienteClinico).filter(ExpedienteClinico.id == consulta.expediente_id).first():
        raise HTTPException(status_code=404, detail="ExpedienteClinico not found")

    resultados = _calcular_resultados_consulta(consulta, paciente)
    
    # Crear consulta con riesgo calculado
    new_consulta = Consulta(
        **consulta.model_dump(exclude={"pam"}),
        pam=resultados["pam"],
        riesgo=resultados["riesgo_enum"],
        score_total=resultados["score_total"],
    )
    db.add(new_consulta)
    db.commit()
    db.refresh(new_consulta)

    _adjuntar_resultados_a_consulta(new_consulta, resultados)
    
    # NOTIFICACIÓN AUTOMÁTICA
    crear_notificacion(
    db,
    consulta.paciente_id,
    TipoNotificacionEnum.INFORMATIVA,
    "Consulta registrada correctamente",
    consulta_id=new_consulta.id
    )

    return new_consulta
@consulta_router.get("/consultas/", response_model=list[ConsultaResponse])
def read_consultas(
    skip: int = 0,
    limit: int | None = None,
    db: Session = Depends(get_db),  # 🔐 seguridad
):
    query = db.query(Consulta).offset(skip)
    if limit is not None:
        query = query.limit(limit)

    consultas = query.all()
    
    for consulta in consultas:
        paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
        if not paciente:
            consulta.riesgo = normalizar_riesgo_enum(consulta.riesgo)
            continue

        resultados = _calcular_resultados_consulta(consulta, paciente)
        _adjuntar_resultados_a_consulta(consulta, resultados)
    
    return consultas

@consulta_router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def read_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")

    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")

    resultados = _calcular_resultados_consulta(consulta, paciente)
    _adjuntar_resultados_a_consulta(consulta, resultados)
    return consulta

@consulta_router.put("/consultas/{consulta_id}", response_model=ConsultaResponse)
def update_consulta(consulta_id: int, consulta_data: ConsultaCreate, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")

    paciente = db.query(Paciente).filter(Paciente.id == consulta_data.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")

    if not db.query(ExpedienteClinico).filter(ExpedienteClinico.id == consulta_data.expediente_id).first():
        raise HTTPException(status_code=404, detail="ExpedienteClinico not found")

    for key, value in consulta_data.model_dump(exclude={"pam"}).items():
        setattr(consulta, key, value)

    resultados = _calcular_resultados_consulta(consulta, paciente)
    consulta.pam = resultados["pam"]
    consulta.riesgo = resultados["riesgo_enum"]
    consulta.score_total = resultados["score_total"]

    # Fuerza recalculo en /prediccion para evitar interpretaciones desactualizadas
    consulta.interpretacion = None

    db.commit()
    db.refresh(consulta)

    _adjuntar_resultados_a_consulta(consulta, resultados)
    return consulta

@consulta_router.delete("/consultas/{consulta_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")
    db.delete(consulta)
    db.commit()
    return


@consulta_router.get("/consultas/{consulta_id}/prediccion")
def prediccion_consulta(consulta_id: int, db: Session = Depends(get_db)):
    try:
        consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
        if not consulta:
            raise HTTPException(status_code=404, detail="Consulta not found")

        paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente not found")

        riesgo_actual = normalizar_riesgo_enum(consulta.riesgo)
        if not isinstance(consulta.riesgo, RiesgoEnum):
            consulta.riesgo = riesgo_actual
            db.commit()
            db.refresh(consulta)

        datos_prediccion = _armar_datos_prediccion(consulta, paciente)
        resultados = _calcular_resultados_consulta(consulta, paciente)

        hubo_cambios = False
        if consulta.pam != resultados["pam"]:
            consulta.pam = resultados["pam"]
            hubo_cambios = True
        if consulta.riesgo != resultados["riesgo_enum"]:
            consulta.riesgo = resultados["riesgo_enum"]
            hubo_cambios = True
        if consulta.score_total != resultados["score_total"]:
            consulta.score_total = resultados["score_total"]
            hubo_cambios = True

        prediccion = generar_prediccion_gemini(datos_prediccion)
        if not prediccion:
            raise Exception("Predicción vacía")

        interpretacion = str(prediccion.get("interpretacion") or "Sin interpretación disponible")
        if consulta.interpretacion != interpretacion:
            consulta.interpretacion = interpretacion
            hubo_cambios = True

        if hubo_cambios:
            db.commit()
            db.refresh(consulta)

        return {
            "consulta_id": consulta.id,
            "paciente_id": consulta.paciente_id,
            "interpretacion": interpretacion,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERROR EN PREDICCION:", e)

        return {
            "consulta_id": consulta_id,
            "paciente_id": None,
            "interpretacion": f"Error en backend: {e}",
        }

