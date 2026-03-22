from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Paciente import Paciente
from app.schemas.paciente_schema import PacienteCreate, PacienteResponse

paciente_router = APIRouter()

@paciente_router.post("/pacientes/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(paciente: PacienteCreate, db: Session = Depends(get_db)):
    new_paciente = Paciente(**paciente.dict())
    db.add(new_paciente)
    db.commit()
    db.refresh(new_paciente)
    return new_paciente

@paciente_router.get("/pacientes/", response_model=list[PacienteResponse])
def read_pacientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Paciente).offset(skip).limit(limit).all()

@paciente_router.get("/pacientes/{paciente_id}", response_model=PacienteResponse)
def read_paciente(paciente_id: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")
    return paciente

@paciente_router.put("/pacientes/{paciente_id}", response_model=PacienteResponse)
def update_paciente(paciente_id: int, paciente_data: PacienteCreate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")
    for key, value in paciente_data.dict().items():
        setattr(paciente, key, value)
    db.commit()
    db.refresh(paciente)
    return paciente

@paciente_router.delete("/pacientes/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paciente(paciente_id: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente not found")
    db.delete(paciente)
    db.commit()
    return
