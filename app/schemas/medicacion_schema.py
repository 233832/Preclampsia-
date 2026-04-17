from pydantic import BaseModel
from typing import List, Optional

class Medicamento(BaseModel):
    nombre: str
    dosis: Optional[str] = None
    max: Optional[str] = None
    frecuencia: Optional[str] = None
    inicio: Optional[str] = None
    horario: Optional[str] = None
    suspension: Optional[str] = None
    alerta: Optional[str] = None

class GrupoMedicamento(BaseModel):
    grupo: str
    medicamentos: List[Medicamento]

class MedicacionResponse(BaseModel):
    estado: str
    detalle: List[GrupoMedicamento]