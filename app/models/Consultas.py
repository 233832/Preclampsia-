from app.shared.config.database import Base
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

class RiesgoEnum(enum.Enum):
    NINGUNO = "Ninguno"
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"


class Consulta(Base):
    __tablename__ = "consultas"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relación con paciente
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)

    # Relación con expediente clínico
    expediente_id = Column(Integer, ForeignKey("expedientes_clinicos.id", ondelete="CASCADE"), nullable=False)

    # Datos de la consulta
    fecha_hora_consulta = Column(DateTime, nullable=False)

    # Datos obstétricos
    edad_madre = Column(Integer, nullable=False)
    edad_gestacional = Column(Integer, nullable=False)

    # Datos físicos
    altura = Column(Float, nullable=False)
    peso = Column(Float, nullable=False)
    imc = Column(Float, nullable=False)

    # Presión arterial
    presion_sistolica = Column(Integer, nullable=False)
    presion_diastolica = Column(Integer, nullable=False)

    # Riesgo de preeclampsia (calculado automáticamente)
    riesgo = Column(Enum(RiesgoEnum), nullable=False, default=RiesgoEnum.NINGUNO)

    # Relaciones
    paciente = relationship("Paciente", back_populates="consultas")
    expediente = relationship("ExpedienteClinico", back_populates="consultas")
    notificaciones = relationship("Notificacion", back_populates="consulta")
    
    # Resultados de IA
    interpretacion = Column(Text, nullable=True)
    score_total = Column(Float, nullable=True)
    
    # Relación con notas de paciente
    notas = relationship("NotaPaciente", back_populates="consulta", cascade="all, delete")
    