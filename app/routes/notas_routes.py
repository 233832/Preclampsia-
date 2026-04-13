from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.shared.config.database import SessionLocal

from app.models.NotasPaciente import NotaPaciente
from app.models.Consultas import Consulta
from app.models.Paciente import Paciente

from app.schemas.notas_schema import NotaCreate, NotaResponse, NotaUpdate


router = APIRouter(prefix="/notas")

# conexión DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Crear nota
@router.post("/", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
def crear_nota(nota: NotaCreate, db: Session = Depends(get_db)):

    # 🔍 validar que exista la consulta
    consulta = db.query(Consulta).filter(Consulta.id == nota.consulta_id).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")

    # 🔍 validar que exista el paciente
    paciente = db.query(Paciente).filter(Paciente.id == nota.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    nueva_nota = NotaPaciente(
        consulta_id=nota.consulta_id,
        paciente_id=nota.paciente_id,
        contenido=nota.contenido
    )

    db.add(nueva_nota)
    db.commit()
    db.refresh(nueva_nota)

    return nueva_nota

# Obtener notas por consulta
@router.get("/consulta/{consulta_id}", response_model=list[NotaResponse])
def obtener_notas_por_consulta(consulta_id: int, db: Session = Depends(get_db)):

    notas = db.query(NotaPaciente).filter(
        NotaPaciente.consulta_id == consulta_id
    ).order_by(NotaPaciente.fecha_creacion.desc()).all()

    return notas

# Eliminar nota
@router.delete("/{nota_id}", status_code=status.HTTP_200_OK)
def eliminar_nota(nota_id: int, db: Session = Depends(get_db)):

    nota = db.query(NotaPaciente).filter(NotaPaciente.id == nota_id).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    db.delete(nota)
    db.commit()

    return {"mensaje": "Nota eliminada correctamente"}

@router.put("/{nota_id}", response_model=NotaResponse)
def actualizar_nota(nota_id: int, nota: NotaUpdate, db: Session = Depends(get_db)):

    nota_db = db.query(NotaPaciente).filter(NotaPaciente.id == nota_id).first()

    if not nota_db:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    nota_db.contenido = nota.contenido

    db.commit()
    db.refresh(nota_db)

    return nota_db