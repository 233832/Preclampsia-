from pydantic import BaseModel, ConfigDict

class ExpedienteClinicoBase(BaseModel):
    paciente_id: int
    model_config = ConfigDict(from_attributes=True)

class ExpedienteClinicoCreate(ExpedienteClinicoBase):
    pass

class ExpedienteClinicoResponse(ExpedienteClinicoBase):
    id: int
