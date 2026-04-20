from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.config.database import SessionLocal
from app.models.Consultas import Consulta
from app.models.Configuraciones import Configuracion
from app.models.Notificaciones import Notificacion, TipoNotificacionEnum


router = APIRouter(prefix="/actualizar")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def crear_notificacion(db, paciente_id, tipo, mensaje, consulta_id=None):
    notif = Notificacion(
        paciente_id=paciente_id,
        tipo=tipo,
        mensaje=mensaje,
        consulta_id=consulta_id
    )
    db.add(notif)


@router.post("/{consulta_id}")
def actualizar_consulta(consulta_id: int, db: Session = Depends(get_db)):

    # 1. Obtener consulta
    consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()

    if not consulta:
        return {"error": "Consulta no encontrada"}

    # 2. Obtener configuración
    config = db.query(Configuracion).first()

    if not config:
        config = Configuracion()
        db.add(config)
        db.commit()
        db.refresh(config)

    # 3. Evaluar reglas clínicas

    #  Riesgo alto
    if consulta.riesgo.name == "ALTO" and config.criticas:
        crear_notificacion(
            db,
            consulta.paciente_id,
            TipoNotificacionEnum.CRITICA,
            "Nivel de riesgo alto detectado",
            consulta.id
        )

    #  Presión alta
    if (
        consulta.presion_sistolica >= config.umbral_sistolico or
        consulta.presion_diastolica >= config.umbral_diastolico
    ) and config.advertencias:

        crear_notificacion(
            db,
            consulta.paciente_id,
            TipoNotificacionEnum.ADVERTENCIA,
            "Presión arterial elevada detectada",
            consulta.id
        )

    #  Seguimiento
    if config.informativas:
        crear_notificacion(
            db,
            consulta.paciente_id,
            TipoNotificacionEnum.INFORMATIVA,
            "Consulta registrada correctamente",
            consulta.id
        )

    # 4. Guardar cambios
    db.commit()

    return {
        "mensaje": "Actualización completada",
        "consulta_id": consulta.id
    }