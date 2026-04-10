from app.shared.config.database import Base
from sqlalchemy import Column, Integer, Boolean


class Configuracion(Base):
    __tablename__ = "configuraciones"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Umbrales clínicos
    umbral_sistolico = Column(Integer, nullable=False, default=140)
    umbral_diastolico = Column(Integer, nullable=False, default=90)

    # Frecuencia de seguimiento (en días)
    frecuencia_dias = Column(Integer, nullable=False, default=14)

    # Configuración de notificaciones
    notificaciones_activas = Column(Boolean, default=True)
    criticas = Column(Boolean, default=True)
    advertencias = Column(Boolean, default=True)
    informativas = Column(Boolean, default=True)