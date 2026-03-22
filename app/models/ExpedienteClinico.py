from app.shared.config.database import Base
from sqlalchemy import Column, Integer, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship


class ExpedienteClinico(Base):
    __tablename__ = "expedientes_clinicos"

    id = Column(Integer, primary_key=True, autoincrement=True)


    # 🔑 Relación con paciente (1 a 1)
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Relaciones
    paciente = relationship("Paciente", back_populates="expediente")
    consultas = relationship("Consulta", back_populates="expediente")


    #class Recipie(Base):
    #    __tablename__ = "recipies"
    #    
    #    id = Column(Integer, primary_key=True, autoincrement=True)
    #    name = Column(String(100), nullable=False)
    #    description = Column(String(255), nullable=False)
    #    ingredients = Column(String(500), nullable=False)
    #    instructions = Column(String(1000), nullable=False)
    #    scheduled_datetime = Column(DateTime, nullable=True)  
    #    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)