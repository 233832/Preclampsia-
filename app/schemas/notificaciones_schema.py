from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificacionBase(BaseModel):
    paciente_id: int
    tipo: str
    mensaje: str
    consulta_id: Optional[int] = None


class NotificacionResponse(NotificacionBase):
    id: int
    paciente_nombre: str
    fecha: datetime
    leida: bool

    class Config:
        from_attributes = True