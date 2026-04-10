from sqlalchemy.orm import Session
from app.models.Notificaciones import Notificacion, TipoNotificacionEnum


def crear_notificacion(db: Session, paciente_id: int, tipo: TipoNotificacionEnum, mensaje: str, consulta_id: int = None):
    nueva = Notificacion(
        paciente_id=paciente_id,
        tipo=tipo,
        mensaje=mensaje,
        consulta_id=consulta_id
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva