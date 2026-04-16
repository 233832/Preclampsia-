from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.config.database import SessionLocal
from app.models.Configuraciones import Configuracion
from app.schemas.configuraciones_schema import ConfiguracionBase, ConfiguracionResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/configuraciones", dependencies=[Depends(get_current_user)])

def serialize_configuracion(config: Configuracion) -> dict:
    return {
        "id": config.id,
        "umbral_sistolico": config.umbral_sistolico,
        "umbral_diastolico": config.umbral_diastolico,
        "notificaciones_activas": bool(
            config.criticas or config.advertencias or config.informativas
        ),
        "criticas": config.criticas,
        "advertencias": config.advertencias,
        "informativas": config.informativas,
        "frecuencia_ninguno": config.frecuencia_ninguno,
        "frecuencia_medio": config.frecuencia_medio,
        "frecuencia_alto": config.frecuencia_alto,
        "nombre_sistema": config.nombre_sistema,
        "version": config.version,
        "descripcion": config.descripcion,
    }


# 🔌 Conexión a DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🟢 GET → obtener configuración
@router.get("/", response_model=ConfiguracionResponse)
def get_configuracion(db: Session = Depends(get_db)):
    config = db.query(Configuracion).first()

    # Si no existe, crear una por defecto
    if not config:
        config = Configuracion()
        db.add(config)
        db.commit()
        db.refresh(config)

    return serialize_configuracion(config)


# 🔵 PUT → actualizar configuración
@router.put("/", response_model=ConfiguracionResponse)
def update_configuracion(data: ConfiguracionBase, db: Session = Depends(get_db)):
    config = db.query(Configuracion).first()

    if not config:
        config = Configuracion()

    # 🟡 Umbrales
    config.umbral_sistolico = data.umbral_sistolico
    config.umbral_diastolico = data.umbral_diastolico

    # 🔴 Notificaciones
    if data.notificaciones_activas:
        config.criticas = data.criticas
        config.advertencias = data.advertencias
        config.informativas = data.informativas
    else:
        config.criticas = False
        config.advertencias = False
        config.informativas = False

    # 🟡 Seguimiento (NUEVO)
    config.frecuencia_ninguno = data.frecuencia_ninguno
    config.frecuencia_medio = data.frecuencia_medio
    config.frecuencia_alto = data.frecuencia_alto

    # 🔵 Sistema (NUEVO)
    config.nombre_sistema = data.nombre_sistema
    config.version = data.version
    config.descripcion = data.descripcion

    db.add(config)
    db.commit()
    db.refresh(config)

    return serialize_configuracion(config)