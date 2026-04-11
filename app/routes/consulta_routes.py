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

consulta_router = APIRouter()

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

        htn = 1 if paciente.hipertension_previa else 0
        diabetes = 1 if paciente.diabetes else 0
        fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0

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
        print("ERROR EN ENDPOINT /consultas/{consulta_id}/prediccion:", e)

        return {
            "consulta_id": consulta_id,
            "paciente_id": None,
            "riesgo": "NINGUNO",
            "riesgo_ml": "NINGUNO",
            "score_total": 0,
            "confianza_ml": 0,
            "interpretacion": f"Error en backend: {e}",
            "datos_consulta": {}
        }