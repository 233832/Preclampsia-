from pydantic import BaseModel


class ConfiguracionBase(BaseModel):
    umbral_sistolico: int
    umbral_diastolico: int
    frecuencia_dias: int
    notificaciones_activas: bool
    criticas: bool
    advertencias: bool
    informativas: bool


class ConfiguracionResponse(ConfiguracionBase):
    id: int

    class Config:
        from_attributes = True