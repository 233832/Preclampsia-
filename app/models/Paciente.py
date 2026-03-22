from app.shared.config.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Datos personales
    nombre = Column(String(150), nullable=False)
    edad = Column(Integer, nullable=False)
    domicilio = Column(String(200), nullable=False)
    estado_civil = Column(String(50), nullable=False)
    ciudad = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False)

    # 🧬 Antecedentes médicos (ahora aquí)
    hipertension_previa = Column(Boolean, default=False)
    diabetes = Column(Boolean, default=False)
    antecedentes_familia_hipertension = Column(Boolean, default=False)

    # Relaciones
    consultas = relationship("Consulta", back_populates="paciente", cascade="all, delete-orphan")
    expediente = relationship("ExpedienteClinico", back_populates="paciente", uselist=False, cascade="all, delete-orphan")
