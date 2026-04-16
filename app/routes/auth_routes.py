from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.shared.config.database import get_db
from app.models.Usuario import Usuario
from app.schemas.usuario_schema import UsuarioCreate, UsuarioLogin, UsuarioResponse
from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token
)

router = APIRouter(prefix="/auth")


# 🔹 REGISTRO
@router.post("/register", response_model=UsuarioResponse)
def register(user: UsuarioCreate, db: Session = Depends(get_db)):

    existing_user = db.query(Usuario).filter(Usuario.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    hashed_password = get_password_hash(user.password)

    new_user = Usuario(
        email=user.email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# 🔹 LOGIN
@router.post("/login")
def login(user: UsuarioLogin, db: Session = Depends(get_db)):

    db_user = db.query(Usuario).filter(Usuario.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    token = create_access_token(data={"sub": db_user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }