from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum

class RiesgoEnum(str, Enum):
    NINGUNO = "Ninguno"
    MEDIO = "Medio"
    ALTO = "Alto"
    HOSPITALIZACION = "Hospitalizacion"

class ConsultaBase(BaseModel):
    paciente_id: int
    expediente_id: int
    fecha_hora_consulta: datetime
    edad_madre: int
    edad_gestacional: int
    altura: float
    peso: float
    imc: float
    presion_sistolica: int
    presion_diastolica: int
    pam: float
    recomendacion_doctor: str | None = None
    incluir_medicacion_sugerida: bool = True
    incluir_recomendacion_doctor: bool = True
    model_config = ConfigDict(from_attributes=True)

class ConsultaCreate(ConsultaBase):
    pass

class ConsultaResponse(ConsultaBase):
    id: int
    riesgo: RiesgoEnum
    score_total: float | None = None
    riesgo_ml: str | None = None
    riesgo_ml_modelo: str | None = None
    confianza_ml: float | None = None
    interpretacion: str | None = None


class ConsultaMedicacionUpdate(BaseModel):
    recomendacion_doctor: str | None = None
    incluir_medicacion_sugerida: bool | None = None
    incluir_recomendacion_doctor: bool | None = None

    model_config = ConfigDict(from_attributes=True)
