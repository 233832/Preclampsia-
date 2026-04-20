from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.shared.config.database import get_db
from app.models.ExpedienteClinico import ExpedienteClinico
from app.models.Paciente import Paciente
from app.schemas.expediente_schema import ExpedienteClinicoCreate, ExpedienteClinicoResponse


expediente_router = APIRouter()


@expediente_router.post("/expedientes/", response_model=ExpedienteClinicoResponse, status_code=status.HTTP_201_CREATED)
def create_expediente(expediente: ExpedienteClinicoCreate, db: Session = Depends(get_db)):
    existing_paciente = db.query(Paciente).filter(Paciente.id == expediente.paciente_id).first()
    if not existing_paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")

    existing_expediente = db.query(ExpedienteClinico).filter(
        ExpedienteClinico.paciente_id == expediente.paciente_id
    ).first()
    if existing_expediente:
        raise HTTPException(status_code=409, detail="Paciente already has an expediente")

    try:
        new_expediente = ExpedienteClinico(**expediente.dict())
        db.add(new_expediente)
        db.commit()
        db.refresh(new_expediente)
        return new_expediente
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Paciente already has an expediente")

@expediente_router.get("/expedientes/", response_model=list[ExpedienteClinicoResponse])
def read_expedientes(skip: int = 0, limit: int | None = None, db: Session = Depends(get_db)):
    query = db.query(ExpedienteClinico).offset(skip)
    if limit is not None:
        query = query.limit(limit)

    return query.all()

@expediente_router.get("/expedientes/{expediente_id}", response_model=ExpedienteClinicoResponse)
def read_expediente(expediente_id: int, db: Session = Depends(get_db)):
    expediente = db.query(ExpedienteClinico).filter(ExpedienteClinico.id == expediente_id).first()
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente not found")
    return expediente

@expediente_router.put("/expedientes/{expediente_id}", response_model=ExpedienteClinicoResponse)
def update_expediente(expediente_id: int, expediente_data: ExpedienteClinicoCreate, db: Session = Depends(get_db)):
    expediente = db.query(ExpedienteClinico).filter(ExpedienteClinico.id == expediente_id).first()
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente not found")
    for key, value in expediente_data.dict().items():
        setattr(expediente, key, value)
    db.commit()
    db.refresh(expediente)
    return expediente

@expediente_router.delete("/expedientes/{expediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expediente(expediente_id: int, db: Session = Depends(get_db)):
    expediente = db.query(ExpedienteClinico).filter(ExpedienteClinico.id == expediente_id).first()
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente not found")
    db.delete(expediente)
    db.commit()
    return
