from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.config.database import SessionLocal
from app.models.Configuraciones import Configuracion
from app.schemas.configuraciones_schema import ConfiguracionBase, ConfiguracionResponse

router = APIRouter(prefix="/configuraciones")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=ConfiguracionResponse)
def get_configuracion(db: Session = Depends(get_db)):
    config = db.query(Configuracion).first()

    if not config:
        config = Configuracion()
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("/", response_model=ConfiguracionResponse)
def update_configuracion(data: ConfiguracionBase, db: Session = Depends(get_db)):
    config = db.query(Configuracion).first()

    if not config:
        config = Configuracion()

    config.umbral_sistolico = data.umbral_sistolico
    config.umbral_diastolico = data.umbral_diastolico
    config.frecuencia_dias = data.frecuencia_dias
    config.notificaciones_activas = data.notificaciones_activas
    config.criticas = data.criticas
    config.advertencias = data.advertencias
    config.informativas = data.informativas

    db.add(config)
    db.commit()
    db.refresh(config)

    return config