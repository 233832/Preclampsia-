from pydantic import BaseModel, ConfigDict, Field, field_validator

TIPOS_SANGRE_VALIDOS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

class PacienteBase(BaseModel):
    nombre: str
    edad: int
    domicilio: str = "No especificado"
    estado_civil: str = "No especificado"
    ciudad: str = "No especificado"
    telefono: str = "No especificado"
    tipo_sangre: str | None = Field(default=None, max_length=5)
    abortos_previos: int = Field(default=0, ge=0)
    cesarea_previos: int = Field(default=0, ge=0)
    embarazos_previos: int = Field(default=0, ge=0)
    partos_previos: int = Field(default=0, ge=0)

    hipertension_previa: bool = False
    diabetes: bool = False
    antecedentes_familia_hipertension: bool = False
    fam_cardiopatia: bool = False
    enf_renal_cronica: bool = False
    embarazo_multiple: bool = False
    muerte_fetal: bool = False
    restriccion_fetal: bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_validator("domicilio", "estado_civil", "ciudad", "telefono", mode="before")
    @classmethod
    def normalizar_campos_texto(cls, value: str | None) -> str:
        if value is None:
            return "No especificado"

        texto = str(value).strip()
        if not texto:
            return "No especificado"

        return texto

    @field_validator("tipo_sangre")
    @classmethod
    def validar_tipo_sangre(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalizado = value.strip().upper()
        if not normalizado:
            return None

        if normalizado not in TIPOS_SANGRE_VALIDOS:
            raise ValueError("tipo_sangre invalido. Usa: A+, A-, B+, B-, AB+, AB-, O+, O-")

        return normalizado

class PacienteCreate(PacienteBase):
    pass

class PacienteResponse(PacienteBase):
    id: int
