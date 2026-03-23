from app.shared.config.database import Base
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship


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

    # Relaciones
    paciente = relationship("Paciente", back_populates="consultas")
    expediente = relationship("ExpedienteClinico", back_populates="consultas")