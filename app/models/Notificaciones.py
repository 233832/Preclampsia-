from app.shared.config.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from sqlalchemy import Enum


class TipoNotificacionEnum(enum.Enum):
    CRITICA = "critica"
    ADVERTENCIA = "advertencia"
    INFORMATIVA = "informativa"


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relación con paciente
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)

    # Relación opcional con consulta
    consulta_id = Column(Integer, ForeignKey("consultas.id", ondelete="CASCADE"), nullable=True)

    # Tipo de notificación
    tipo = Column(Enum(TipoNotificacionEnum), nullable=False)

    # Contenido
    mensaje = Column(String(255), nullable=False)

    # Fecha
    fecha = Column(DateTime, default=datetime.now)

    # Estado
    leida = Column(Boolean, default=False)

    # Relaciones
    paciente = relationship("Paciente", back_populates="notificaciones")
    consulta = relationship("Consulta", back_populates="notificaciones")