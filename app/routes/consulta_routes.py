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
from app.services.auth_service import get_current_user

consulta_router = APIRouter(dependencies=[Depends(get_current_user)])


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
    if not db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first():
        raise HTTPException(status_code=404, detail="Paciente not found")
    if not db.query(ExpedienteClinico).filter(ExpedienteClinico.id == consulta.expediente_id).first():
        raise HTTPException(status_code=404, detail="ExpedienteClinico not found")

    # Obtener datos del paciente para cálculo de riesgo
    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    
    # Convertir booleanos a 0/1
    htn = 1 if paciente.hipertension_previa else 0
    diabetes = 1 if paciente.diabetes else 0
    fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0
    fam_cardio = 1 if paciente.fam_cardiopatia else 0
    renal = 1 if paciente.enf_renal_cronica else 0
    multiple = 1 if paciente.embarazo_multiple else 0
    muerte = 1 if paciente.muerte_fetal else 0
    rcf = 1 if paciente.restriccion_fetal else 0
    pam = (consulta.presion_sistolica + 2 * consulta.presion_diastolica) / 3
    
    # Calcular riesgo
    riesgo_str, _ = clasificar_riesgo(
        {
            "age": consulta.edad_madre,
            "bmi": consulta.imc,
            "sysbp": consulta.presion_sistolica,
            "diabp": consulta.presion_diastolica,
            "presion_art_media": pam,
            "htn": htn,
            "diabetes": diabetes,
            "fam_htn": fam_htn,
            "fam_cardiopatia": fam_cardio,
            "enf_renal_cronica": renal,
            "embarazo_multiple": multiple,
            "muerte_fetal": muerte,
            "restriccion_fetal": rcf,
        }
    )
    
    # Mapear string a enum
    riesgo_enum = normalizar_riesgo_enum(riesgo_str)
    
    # Crear consulta con riesgo calculado
    new_consulta = Consulta(
        **consulta.dict(exclude={"pam"}),
        pam=pam,
        riesgo=riesgo_enum
    )
    db.add(new_consulta)
    db.commit()
    db.refresh(new_consulta)
    
    # NOTIFICACIÓN AUTOMÁTICA
    crear_notificacion(
    db,
    consulta.paciente_id,
    TipoNotificacionEnum.INFORMATIVA,
    "Consulta registrada correctamente",
    consulta_id=new_consulta.id
    )

    return new_consulta

from app.services.auth_service import get_current_user

@consulta_router.get("/consultas/", response_model=list[ConsultaResponse])
def read_consultas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),  # 🔐 seguridad
):
    consultas = db.query(Consulta).offset(skip).limit(limit).all()
    
    for consulta in consultas:
        consulta.riesgo = normalizar_riesgo_enum(consulta.riesgo)
    
    return consultas

@consulta_router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def read_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")
    consulta.riesgo = normalizar_riesgo_enum(consulta.riesgo)
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

    htn = 1 if paciente.hipertension_previa else 0
    diabetes = 1 if paciente.diabetes else 0
    fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0
    fam_cardio = 1 if paciente.fam_cardiopatia else 0
    renal = 1 if paciente.enf_renal_cronica else 0
    multiple = 1 if paciente.embarazo_multiple else 0
    muerte = 1 if paciente.muerte_fetal else 0
    rcf = 1 if paciente.restriccion_fetal else 0

    pam = (consulta.presion_sistolica + 2 * consulta.presion_diastolica) / 3
    consulta.pam = pam

    riesgo_str, _ = clasificar_riesgo(
        {
            "age": consulta.edad_madre,
            "bmi": consulta.imc,
            "sysbp": consulta.presion_sistolica,
            "diabp": consulta.presion_diastolica,
            "presion_art_media": pam,
            "htn": htn,
            "diabetes": diabetes,
            "fam_htn": fam_htn,
            "fam_cardiopatia": fam_cardio,
            "enf_renal_cronica": renal,
            "embarazo_multiple": multiple,
            "muerte_fetal": muerte,
            "restriccion_fetal": rcf,
        }
    )
    consulta.riesgo = normalizar_riesgo_enum(riesgo_str)

    # Fuerza recalculo en /prediccion para evitar interpretaciones desactualizadas
    consulta.interpretacion = None
    consulta.score_total = None

    db.commit()
    db.refresh(consulta)
    consulta.riesgo = normalizar_riesgo_enum(consulta.riesgo)
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

        # Preparar datos para score/riesgo ML y predicción completa
        htn = 1 if paciente.hipertension_previa else 0
        diabetes = 1 if paciente.diabetes else 0
        fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0
        fam_cardio = 1 if paciente.fam_cardiopatia else 0
        renal = 1 if paciente.enf_renal_cronica else 0
        multiple = 1 if paciente.embarazo_multiple else 0
        muerte = 1 if paciente.muerte_fetal else 0
        rcf = 1 if paciente.restriccion_fetal else 0
        pam = consulta.pam if consulta.pam is not None and consulta.pam > 0 else (
            (consulta.presion_sistolica + 2 * consulta.presion_diastolica) / 3
        )
        datos_prediccion = {
            "age": consulta.edad_madre,
            "bmi": consulta.imc,
            "sysbp": consulta.presion_sistolica,
            "diabp": consulta.presion_diastolica,
            "presion_art_media": pam,
            "htn": htn,
            "diabetes": diabetes,
            "fam_htn": fam_htn,
            "fam_cardiopatia": fam_cardio,
            "enf_renal_cronica": renal,
            "embarazo_multiple": multiple,
            "muerte_fetal": muerte,
            "restriccion_fetal": rcf,
        }

        riesgo_reglas_str, score_reglas = clasificar_riesgo(datos_prediccion)
        riesgo_reglas = normalizar_riesgo_enum(riesgo_reglas_str)

        hubo_cambios = False
        if consulta.pam != pam:
            consulta.pam = pam
            hubo_cambios = True
        if consulta.riesgo != riesgo_reglas:
            consulta.riesgo = riesgo_reglas
            hubo_cambios = True
        if consulta.score_total != score_reglas:
            consulta.score_total = score_reglas
            hubo_cambios = True

        if hubo_cambios:
            db.commit()
            db.refresh(consulta)

        riesgo_ml_modelo_actual, confianza_ml_actual = predecir_riesgo_ml(datos_prediccion)
        riesgo_ml_alineado = riesgo_reglas.name

        # 1. EVITAR VOLVER A USAR IA (CLAVE)
        if consulta.interpretacion and consulta.score_total is not None:
            return {
                "consulta_id": consulta.id,
                "paciente_id": consulta.paciente_id,
                "riesgo": riesgo_reglas.name,
                "riesgo_ml": riesgo_ml_alineado,
                "riesgo_ml_modelo": riesgo_ml_modelo_actual,
                "score_total": score_reglas,
                "confianza_ml": confianza_ml_actual,
                "interpretacion": consulta.interpretacion,
                "datos_consulta": {
                    "edad_madre": consulta.edad_madre,
                    "imc": consulta.imc,
                    "presion_sistolica": consulta.presion_sistolica,
                    "presion_diastolica": consulta.presion_diastolica,
                    "hipertension_previa": bool(htn),
                    "diabetes": bool(diabetes),
                    "antecedentes_familia_hipertension": bool(fam_htn),
                },
            }

        # 3. Generar predicción (IA SOLO UNA VEZ)
        prediccion = generar_prediccion_gemini(datos_prediccion)

        if not prediccion:
            raise Exception("Predicción vacía")

        riesgo_predicho = normalizar_riesgo_enum(prediccion.get("riesgo"))

        # 4. GUARDAR RESULTADO (CLAVE)
        consulta.riesgo = riesgo_predicho
        consulta.interpretacion = prediccion["interpretacion"]
        consulta.score_total = prediccion["score_total"]

        db.commit()

        # 5. Retornar
        return {
            "consulta_id": consulta.id,
            "paciente_id": consulta.paciente_id,
            "riesgo": riesgo_predicho.name,
            "riesgo_ml": riesgo_predicho.name,
            "riesgo_ml_modelo": prediccion.get("riesgo_ml", "NO DISPONIBLE"),
            "score_total": prediccion["score_total"],
            "confianza_ml": prediccion["confianza_ml"],
            "interpretacion": prediccion["interpretacion"],
            "datos_consulta": {
                "edad_madre": consulta.edad_madre,
                "imc": consulta.imc,
                "presion_sistolica": consulta.presion_sistolica,
                "presion_diastolica": consulta.presion_diastolica,
                "hipertension_previa": bool(htn),
                "diabetes": bool(diabetes),
                "antecedentes_familia_hipertension": bool(fam_htn),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERROR EN PREDICCION:", e)

        return {
            "consulta_id": consulta_id,
            "paciente_id": None,
            "riesgo": "NINGUNO",
            "riesgo_ml": "NO DISPONIBLE",
            "riesgo_ml_modelo": "NO DISPONIBLE",
            "score_total": 0,
            "confianza_ml": 0,
            "interpretacion": f"Error en backend: {e}",
            "datos_consulta": {}
        }

