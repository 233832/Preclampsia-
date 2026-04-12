from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Consultas import Consulta, RiesgoEnum
from app.models.Paciente import Paciente
from app.models.ExpedienteClinico import ExpedienteClinico
from app.schemas.consulta_schema import ConsultaCreate, ConsultaResponse
from app.services.gemini_service import generar_prediccion_gemini, clasificar_riesgo
from app.services.notificacion_service import crear_notificacion
from app.models.Notificaciones import TipoNotificacionEnum
from fastapi.responses import FileResponse
import base64
import os

consulta_router = APIRouter()


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

    color_map = {
        "NINGUNO": "#95A5A6",
        "BAJO": "#27AE60",
        "MEDIO": "#E67E22",
        "ALTO": "#C0392B",
    }
    riesgo_color = HexColor(color_map.get(riesgo.upper(), "#7F8C8D"))
    pdf.setFillColor(riesgo_color)
    pdf.roundRect(40, y - 6, 180, 24, 6, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, y + 2, str(riesgo).upper())
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
    
    # Calcular riesgo
    riesgo_str = clasificar_riesgo(
        edad=consulta.edad_madre,
        imc=consulta.imc,
        htn=htn,
        diabetes=diabetes,
        fam_htn=fam_htn,
        sysbp=consulta.presion_sistolica,
        diabp=consulta.presion_diastolica,
    )
    
    # Mapear string a enum
    riesgo_enum = RiesgoEnum[riesgo_str.upper()]
    
    # Crear consulta con riesgo calculado
    new_consulta = Consulta(
        **consulta.dict(),
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

@consulta_router.get("/consultas/", response_model=list[ConsultaResponse])
def read_consultas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Consulta).offset(skip).limit(limit).all()

@consulta_router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def read_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")
    return consulta

@consulta_router.put("/consultas/{consulta_id}", response_model=ConsultaResponse)
def update_consulta(consulta_id: int, consulta_data: ConsultaCreate, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")
    for key, value in consulta_data.dict().items():
        setattr(consulta, key, value)
    db.commit()
    db.refresh(consulta)
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

        # 1. EVITAR VOLVER A USAR IA (CLAVE)
        if consulta.interpretacion and consulta.score_total:
            return {
                "consulta_id": consulta.id,
                "paciente_id": consulta.paciente_id,
                "riesgo": consulta.riesgo.name,
                "score_total": consulta.score_total,
                "interpretacion": consulta.interpretacion
            }

        # 2. Preparar datos
        htn = 1 if paciente.hipertension_previa else 0
        diabetes = 1 if paciente.diabetes else 0
        fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0

        # 3. Generar predicción (IA SOLO UNA VEZ)
        prediccion = generar_prediccion_gemini(
            edad=consulta.edad_madre,
            imc=consulta.imc,
            htn=htn,
            diabetes=diabetes,
            fam_htn=fam_htn,
            sysbp=consulta.presion_sistolica,
            diabp=consulta.presion_diastolica,
        )

        if not prediccion:
            raise Exception("Predicción vacía")

        # 4. GUARDAR RESULTADO (CLAVE)
        consulta.interpretacion = prediccion["interpretacion"]
        consulta.score_total = prediccion["score_total"]

        db.commit()

        # 5. Retornar
        return {
            "consulta_id": consulta.id,
            "paciente_id": consulta.paciente_id,
            "riesgo": prediccion["riesgo"],
            "riesgo_ml": prediccion["riesgo_ml"],
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
            "score_total": 0,
            "interpretacion": f"Error en backend: {e}",
            "datos_consulta": {}
        }

