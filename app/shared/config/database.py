from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

db_config = {
    "DB_USER": os.getenv("DB_USER"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    "DB_HOST": os.getenv("DB_HOST"),
    "DB_PORT": os.getenv("DB_PORT"),
    "DB_NAME": os.getenv("DB_NAME"),
}

required_db_vars = ("DB_USER", "DB_HOST", "DB_PORT", "DB_NAME")
missing_db_vars = [key for key in required_db_vars if not db_config.get(key)]
if missing_db_vars:
    missing_vars_text = ", ".join(missing_db_vars)
    raise RuntimeError(
        f"Faltan variables de entorno de base de datos: {missing_vars_text}"
    )

db_password = db_config["DB_PASSWORD"] or ""

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{db_config['DB_USER']}:{db_password}"
    f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{db_config['DB_NAME']}"
)

# Evita conexiones muertas en el pool (causa comun de InterfaceError en rollback).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() 


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()