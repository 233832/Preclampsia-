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
    tipo_sangre = Column(String(5), nullable=True)

    # Antecedentes médicos 
    hipertension_previa = Column(Boolean, default=False)
    diabetes = Column(Boolean, default=False)
    antecedentes_familia_hipertension = Column(Boolean, default=False)
    
# Antecedentes obstétricos
    embarazos_previos = Column(Integer, default=0)
    partos_previos = Column(Integer, default=0)
    abortos_previos = Column(Integer, default=0)
    cesarea_previos = Column(Integer, default=0)
    antecedente_preeclampsia_embarazo_previo = Column(Boolean, default=False)
    
# Antecedentes personales patológicos
    enf_renal_cronica = Column(Boolean, default=False)
    hipertencion_cronica = Column(Boolean, default=False)
    embarazo_multiple = Column("embarazos_multiples", Boolean, default=False)
    muerte_fetal = Column(Boolean, default=False)
    restriccion_fetal = Column(Boolean, default=False)
    
#Antecedentes heredo familiares
    fam_cardiopatia = Column(Boolean, default=False)

    # Relaciones
    consultas = relationship("Consulta", back_populates="paciente", cascade="all, delete-orphan")
    expediente = relationship("ExpedienteClinico", back_populates="paciente", uselist=False, cascade="all, delete-orphan")
    notificaciones = relationship("Notificacion", back_populates="paciente")