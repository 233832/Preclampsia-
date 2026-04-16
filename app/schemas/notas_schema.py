from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# Base
class NotaBase(BaseModel):
    contenido: str = Field(..., min_length=1)

# Crear nota (lo que envía el frontend)
class NotaCreate(NotaBase):
    consulta_id: int
    paciente_id: int


class NotaUpdate(BaseModel):
    contenido: str = Field(..., min_length=1)

# Respuesta del backend
class NotaResponse(NotaBase):
    id: int
    consulta_id: int
    paciente_id: int
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)