
from sqlalchemy import Column, Integer, Boolean, String
from app.shared.config.database import Base


class Configuracion(Base):
    __tablename__ = "configuraciones"

    id = Column(Integer, primary_key=True, index=True)

    # 🟡 Umbrales
    umbral_sistolico = Column(Integer, default=140)
    umbral_diastolico = Column(Integer, default=90)

    # 🔴 Notificaciones
    criticas = Column(Boolean, default=True)
    advertencias = Column(Boolean, default=True)
    informativas = Column(Boolean, default=True)

    # 🟡 🔥 NUEVO → Seguimiento
    # Se mantiene el nombre físico de columna para compatibilidad con BD existente.
    frecuencia_ninguno = Column("frecuencia_bajo", Integer, default=30)   # días
    frecuencia_medio = Column(Integer, default=14)
    frecuencia_alto = Column(Integer, default=7)

    # 🔵 🔥 NUEVO → Sistema
    nombre_sistema = Column(String(100), default="VitaPrenatal")
    version = Column(String(20), default="1.0")
    descripcion = Column(String(255), default="Sistema de monitoreo clínico de preeclampsia")