from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class ConfiguracionBase(BaseModel):
    umbral_sistolico: int
    umbral_diastolico: int

    notificaciones_activas: bool
    criticas: bool
    advertencias: bool
    informativas: bool

    frecuencia_ninguno: int = Field(
        validation_alias=AliasChoices("frecuencia_ninguno", "frecuencia_bajo"),
        serialization_alias="frecuencia_ninguno",
    )
    frecuencia_medio: int
    frecuencia_alto: int

    nombre_sistema: str
    version: str
    descripcion: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConfiguracionResponse(ConfiguracionBase):
    id: int