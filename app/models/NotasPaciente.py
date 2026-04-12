from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.shared.config.database import Base

class NotaPaciente(Base):
    __tablename__ = "notas_paciente"

    id = Column(Integer, primary_key=True, index=True)

    consulta_id = Column(Integer, ForeignKey("consultas.id"), nullable=False)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)

    contenido = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # relaciones
    consulta = relationship("Consulta", back_populates="notas")
    paciente = relationship("Paciente")