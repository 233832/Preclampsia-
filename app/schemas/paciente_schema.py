from pydantic import BaseModel, ConfigDict

class PacienteBase(BaseModel):
    nombre: str
    edad: int
    domicilio: str
    estado_civil: str
    ciudad: str
    telefono: str
    hipertension_previa: bool = False
    diabetes: bool = False
    antecedentes_familia_hipertension: bool = False
    model_config = ConfigDict(from_attributes=True)

class PacienteCreate(PacienteBase):
    pass

class PacienteResponse(PacienteBase):
    id: int
