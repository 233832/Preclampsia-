from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 🔹 HASH
def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 🔹 TOKEN
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

security = HTTPBearer(auto_error=False)

def _token_from_cookie(request: Request) -> str | None:
    cookie_value = request.cookies.get("access_token")
    if not cookie_value:
        return None

    cookie_value = cookie_value.strip()
    if not cookie_value:
        return None

    if cookie_value.lower().startswith("bearer "):
        return cookie_value.split(" ", 1)[1].strip() or None

    return cookie_value


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    token: str | None = None

    if credentials is not None:
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Esquema invalido. Usa Authorization: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
    else:
        token = _token_from_cookie(request)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Falta autenticacion. Envia Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload