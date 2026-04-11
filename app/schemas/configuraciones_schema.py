from pydantic import BaseModel

class ConfiguracionBase(BaseModel):
    umbral_sistolico: int
    umbral_diastolico: int

    notificaciones_activas: bool
    criticas: bool
    advertencias: bool
    informativas: bool

    frecuencia_bajo: int
    frecuencia_medio: int
    frecuencia_alto: int

    nombre_sistema: str
    version: str
    descripcion: str


class ConfiguracionResponse(ConfiguracionBase):
    id: int

    class Config:
        from_attributes = True