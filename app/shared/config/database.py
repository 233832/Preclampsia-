import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

db_config = {
    "DB_USER": os.getenv("DB_USER"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    "DB_HOST": os.getenv("DB_HOST"),
    "DB_PORT": os.getenv("DB_PORT"),
    "DB_NAME": os.getenv("DB_NAME"),
}


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


db_engine_choice = os.getenv("DB_ENGINE", "mysql").lower()

if db_engine_choice == "sqlite":
    SQLALCHEMY_DATABASE_URL = "sqlite:///./preclampsia_dev.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    db_password = db_config.get("DB_PASSWORD") or ""
    db_user = db_config.get("DB_USER") or "root"
    db_host = db_config.get("DB_HOST") or "localhost"
    db_port_str = db_config.get("DB_PORT") or "3306"
    try:
        db_port = int(db_port_str)
    except ValueError:
        db_port = 3306
    db_name = db_config.get("DB_NAME") or "prelampsia_db"

    SQLALCHEMY_DATABASE_URL = (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

    if _is_port_open(db_host, db_port, timeout=0.8):
        try:
            mysql_engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 2},
                pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            )
            with mysql_engine.connect() as conn:
                pass
            engine = mysql_engine
        except Exception as e:
            print(f"[DB WARNING] Error al conectar a MySQL ({e}). Usando SQLite dev database.")
            SQLALCHEMY_DATABASE_URL = "sqlite:///./preclampsia_dev.db"
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
    else:
        print(f"[DB WARNING] Puerto MySQL ({db_host}:{db_port}) cerrado o no responde. Usando SQLite dev database.")
        SQLALCHEMY_DATABASE_URL = "sqlite:///./preclampsia_dev.db"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
