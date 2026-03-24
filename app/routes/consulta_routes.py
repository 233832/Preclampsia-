from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Consultas import Consulta
from app.models.Paciente import Paciente
from app.models.ExpedienteClinico import ExpedienteClinico
from app.schemas.consulta_schema import ConsultaCreate, ConsultaResponse
from app.services.gemini_service import generar_prediccion_gemini, clasificar_riesgo

consulta_router = APIRouter()

@consulta_router.post("/consultas/", response_model=ConsultaResponse, status_code=status.HTTP_201_CREATED)
def create_consulta(consulta: ConsultaCreate, db: Session = Depends(get_db)):
    if not db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first():
        raise HTTPException(status_code=404, detail="Paciente not found")
    if not db.query(ExpedienteClinico).filter(ExpedienteClinico.id == consulta.expediente_id).first():
        raise HTTPException(status_code=404, detail="ExpedienteClinico not found")

    new_consulta = Consulta(**consulta.dict())
    db.add(new_consulta)
    db.commit()
    db.refresh(new_consulta)
    return new_consulta

@consulta_router.get("/consultas/", response_model=list[ConsultaResponse])
def read_consultas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Consulta).offset(skip).limit(limit).all()

@consulta_router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def read_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")

    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    if paciente:
        htn = 1 if paciente.hipertension_previa else 0
        diabetes = 1 if paciente.diabetes else 0
        fam_htn = 1 if paciente.antecedentes_familia_hipertension else 0
        riesgo = clasificar_riesgo(
            consulta.edad_madre,
            consulta.imc,
            htn,
            diabetes,
            fam_htn,
            consulta.presion_sistolica,
            consulta.presion_diastolica,
        )
    else:
        riesgo = None

    data = ConsultaResponse.model_validate(consulta).model_dump()
    data["riesgo"] = riesgo
    return data

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


@consulta_router.get("/consultas/{consulta_id}/prediccion", status_code=status.HTTP_200_OK)
def prediccion_consulta(consulta_id: int, db: Session = Depends(get_db)):
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta not found")

    paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")

    # Convierte los datos relevantes a binarios enteros (0/1)
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

    return {
        "consulta_id": consulta.id,
        "paciente_id": consulta.paciente_id,
        "riesgo": prediccion["riesgo"],
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