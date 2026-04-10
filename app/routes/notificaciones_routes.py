from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.shared.config.database import get_db
from app.models.Notificaciones import Notificacion
from app.schemas.notificaciones_schema import NotificacionResponse

router = APIRouter(prefix="/notificaciones")


@router.get("", response_model=list[NotificacionResponse])
def get_notificaciones(db: Session = Depends(get_db)):

    notificaciones = (
        db.query(Notificacion)
        .options(joinedload(Notificacion.paciente))
        .order_by(Notificacion.fecha.desc())
        .all()
    )

    return [
        {
            "id": n.id,
            "paciente_id": n.paciente_id,
            "paciente_nombre": n.paciente.nombre if n.paciente else "Sin nombre",  # 🔥 FIX
            "tipo": n.tipo.value,
            "mensaje": n.mensaje,
            "consulta_id": n.consulta_id,
            "fecha": n.fecha,
            "leida": n.leida
        }
        for n in notificaciones
    ]


@router.put("/{id}/leida")
def marcar_como_leida(id: int, db: Session = Depends(get_db)):
    notif = db.query(Notificacion).filter(Notificacion.id == id).first()

    if not notif:
        return {"error": "No encontrada"}

    notif.leida = True
    db.commit()
    db.refresh(notif)

    return {"mensaje": "Notificación marcada como leída"}


@router.get("/test")
def test():
    return {"msg": "funciona"}