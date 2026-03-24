from pydantic import BaseModel, ConfigDict
from datetime import datetime

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
    model_config = ConfigDict(from_attributes=True)

class ConsultaCreate(ConsultaBase):
    pass

class ConsultaResponse(ConsultaBase):
    id: int
    riesgo: str | None = None