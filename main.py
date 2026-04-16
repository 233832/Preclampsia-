from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.shared.config.database import engine, Base
from app.routes.paciente_routes import paciente_router
from app.routes.expediente_routes import expediente_router
from app.routes.consulta_routes import consulta_router
from app.routes.notificaciones_routes import router as notificaciones_router
from app.routes.configuraciones_routes import router as configuraciones_router
from app.routes import actualizaciones_routes
from app.routes import notas_routes
from app.routes import reportes_routes
from app.services import gemini_service
from app.routes.auth_routes import router as auth_router

app = FastAPI()


def cargar_modelo_ml_seguro() -> bool:
    try:
        cargar_fn = getattr(gemini_service, "cargar_modelo_ml", None)
        if not callable(cargar_fn):
            print("[ML] cargar_modelo_ml no esta disponible. Se usara fallback.")
            return False

        return bool(cargar_fn(force=True))
    except Exception as exc:
        print(f"[ML] Error al cargar modelo: {exc}. Se usara fallback.")
        return False


def asegurar_campos_obstetricos_enteros() -> None:
    campos_objetivo = [
        "embarazos_previos",
        "partos_previos",
        "abortos_previos",
        "cesarea_previos",
    ]

    try:
        if engine.dialect.name != "mysql":
            print("[DB] Migracion omitida: solo aplica para MySQL.")
            return

        with engine.begin() as conn:
            schema = conn.execute(text("SELECT DATABASE()")).scalar()
            if not schema:
                print("[DB] Migracion omitida: no se detecto schema activo.")
                return

            placeholders = ", ".join([f":col_{i}" for i in range(len(campos_objetivo))])
            params = {"schema": schema}
            params.update({f"col_{i}": col for i, col in enumerate(campos_objetivo)})

            columnas = conn.execute(
                text(
                    f"""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :schema
                      AND TABLE_NAME = 'pacientes'
                      AND COLUMN_NAME IN ({placeholders})
                    """
                ),
                params,
            ).mappings().all()

            info_por_columna = {row["COLUMN_NAME"]: row for row in columnas}

            for columna in campos_objetivo:
                info = info_por_columna.get(columna)
                if not info:
                    continue

                data_type = str(info.get("DATA_TYPE") or "").lower()
                is_nullable = str(info.get("IS_NULLABLE") or "").upper() == "YES"
                default_value = info.get("COLUMN_DEFAULT")
                default_is_zero = str(default_value) == "0"

                if data_type != "int" or is_nullable or not default_is_zero:
                    conn.execute(
                        text(
                            f"ALTER TABLE pacientes MODIFY COLUMN {columna} INT NOT NULL DEFAULT 0"
                        )
                    )

            print("[DB] Migracion de campos obstetricos a enteros verificada.")
    except Exception as exc:
        print(f"[DB] Error aplicando migracion de pacientes: {exc}")


def asegurar_columna_tipo_sangre() -> None:
    try:
        if engine.dialect.name != "mysql":
            print("[DB] Migracion tipo_sangre omitida: solo aplica para MySQL.")
            return

        with engine.begin() as conn:
            schema = conn.execute(text("SELECT DATABASE()")).scalar()
            if not schema:
                print("[DB] Migracion tipo_sangre omitida: no se detecto schema activo.")
                return

            columna = conn.execute(
                text(
                    """
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :schema
                      AND TABLE_NAME = 'pacientes'
                      AND COLUMN_NAME = 'tipo_sangre'
                    """
                ),
                {"schema": schema},
            ).mappings().first()

            if not columna:
                conn.execute(text("ALTER TABLE pacientes ADD COLUMN tipo_sangre VARCHAR(5) NULL"))
                print("[DB] Columna tipo_sangre agregada en pacientes.")
                return

            data_type = str(columna.get("DATA_TYPE") or "").lower()
            max_length = int(columna.get("CHARACTER_MAXIMUM_LENGTH") or 0)
            is_nullable = str(columna.get("IS_NULLABLE") or "").upper() == "YES"

            if data_type != "varchar" or max_length < 5 or not is_nullable:
                conn.execute(text("ALTER TABLE pacientes MODIFY COLUMN tipo_sangre VARCHAR(5) NULL"))
                print("[DB] Columna tipo_sangre ajustada en pacientes.")
            else:
                print("[DB] Columna tipo_sangre verificada.")
    except Exception as exc:
        print(f"[DB] Error aplicando migracion de tipo_sangre: {exc}")


@app.on_event("startup")
def startup_ml_load() -> None:
    asegurar_campos_obstetricos_enteros()
    asegurar_columna_tipo_sangre()
    ml_loaded = cargar_modelo_ml_seguro()
    if ml_loaded:
        print("[ML] Modelo cargado correctamente al iniciar.")
    else:
        print("[ML] No se pudo cargar el modelo al iniciar. Se usara fallback.")


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "API de preeclampsia activa",
        "docs": "/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)

app.include_router(paciente_router, prefix="/api", tags=["pacientes"])
app.include_router(expediente_router, prefix="/api", tags=["expedientes"])
app.include_router(consulta_router, prefix="/api", tags=["consultas"])
app.include_router(notificaciones_router, prefix="/api", tags=["notificaciones"])
app.include_router(configuraciones_router, prefix="/api", tags=["configuraciones"])
app.include_router(actualizaciones_routes.router, prefix="/api", tags=["actualizaciones"])
app.include_router(notas_routes.router, prefix="/api", tags=["notas"])
app.include_router(reportes_routes.router, prefix="/api", tags=["reportes"])
app.include_router(auth_router, prefix="/api", tags=["auth"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)