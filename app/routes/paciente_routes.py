from fastapi import APIRouter, Body, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Paciente import Paciente
from app.schemas.paciente_schema import PacienteCreate, PacienteResponse
from app.services.notificacion_service import crear_notificacion
from app.models.Notificaciones import TipoNotificacionEnum

paciente_router = APIRouter(prefix="/pacientes")

PACIENTE_CREATE_DOCS_EXAMPLE = {
    "nombre": "string",
    "edad": 0,
    "domicilio": "No especificado",
    "estado_civil": "No especificado",
    "ciudad": "No especificado",
    "telefono": "No especificado",
    "tipo_sangre": "A+",
    "abortos_previos": 0,
    "cesarea_previos": 0,
    "embarazos_previos": 0,
    "partos_previos": 0,
    "antecedente_preeclampsia_embarazo_previo": False,
    "hipertension_previa": False,
    "diabetes": False,
    "antecedentes_familia_hipertension": False,
    "fam_cardiopatia": False,
    "enf_renal_cronica": False,
    "embarazo_multiple": False,
    "muerte_fetal": False,
    "restriccion_fetal": False,
}

@paciente_router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(
    paciente: PacienteCreate = Body(
        ...,
        openapi_examples={
            "orden_base": {
                "summary": "Payload base",
                "value": PACIENTE_CREATE_DOCS_EXAMPLE,
            }
        },
    ),
    db: Session = Depends(get_db),
):
    data = paciente.model_dump()  
    new_paciente = Paciente(**data)
    db.add(new_paciente)
    db.commit()
    db.refresh(new_paciente)
    crear_notificacion(
        db,
        new_paciente.id,
        TipoNotificacionEnum.INFORMATIVA,
        "Nuevo paciente registrado"
    )
    return new_paciente

@paciente_router.get("/", response_model=list[PacienteResponse])
def read_pacientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pacientes = db.query(Paciente).offset(skip).limit(limit).all()
    return pacientes

@paciente_router.get("/{paciente_id}", response_model=PacienteResponse)
def read_paciente(paciente_id: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Paciente no encontrado"
        )
    return paciente

@paciente_router.put("/{paciente_id}", response_model=PacienteResponse)
def update_paciente(paciente_id: int, paciente_data: PacienteCreate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Paciente no encontrado"
        )
    update_data = paciente_data.model_dump(exclude_unset=True)
    # Este antecedente se captura solo en alta de paciente y no se modifica despues.
    update_data.pop("antecedente_preeclampsia_embarazo_previo", None)
    for key, value in update_data.items():
        setattr(paciente, key, value)
    db.commit()
    db.refresh(paciente)
    return paciente

@paciente_router.delete("/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paciente(paciente_id: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Paciente no encontrado"
        )
    db.delete(paciente)
    db.commit()
    return