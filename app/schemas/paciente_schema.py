from pydantic import BaseModel, ConfigDict, Field, field_validator

TIPOS_SANGRE_VALIDOS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

PACIENTE_EJEMPLO_VALIDO = {
    "nombre": "",
    "edad": 0,
    "domicilio": "",
    "estado_civil": "",
    "ciudad": "",
    "telefono": "",
    "tipo_sangre": None,
    "abortos_previos": 0,
    "cesarea_previos": 0,
    "embarazos_previos": 0,
    "partos_previos": 0,
    "antecedente_preeclampsia_embarazo_previo": False,
    "hipertension_previa": False,
    "diabetes": False,
    "antecedentes_familia_hipertension": False,
    "fam_cardiopatia": False,
    "enf_renal_cronica": False,
    "embarazo_multiple": False,
    "muerte_fetal": False,
    "restriccion_fetal": False,
}

class PacienteBase(BaseModel):
    nombre: str
    edad: int
    domicilio: str = "No especificado"
    estado_civil: str = "No especificado"
    ciudad: str = "No especificado"
    telefono: str = "No especificado"
    tipo_sangre: str | None = Field(
        default=None,
        max_length=5,
        description="Opcional. Valores validos: A+, A-, B+, B-, AB+, AB-, O+, O-.",
        examples=["A+", "O-"],
    )
    abortos_previos: int = Field(default=0, ge=0)
    cesarea_previos: int = Field(default=0, ge=0)
    embarazos_previos: int = Field(default=0, ge=0)
    partos_previos: int = Field(default=0, ge=0)
    antecedente_preeclampsia_embarazo_previo: bool = False

    hipertension_previa: bool = False
    diabetes: bool = False
    antecedentes_familia_hipertension: bool = False
    fam_cardiopatia: bool = False
    enf_renal_cronica: bool = False
    embarazo_multiple: bool = False
    muerte_fetal: bool = False
    restriccion_fetal: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": PACIENTE_EJEMPLO_VALIDO},
    )

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
