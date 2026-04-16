from pydantic import BaseModel, EmailStr, ConfigDict

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)