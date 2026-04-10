from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.shared.config.database import engine, Base
from app.routes.paciente_routes import paciente_router
from app.routes.expediente_routes import expediente_router
from app.routes.consulta_routes import consulta_router
from app.routes.notificaciones_routes import router as notificaciones_router
from app.routes.configuraciones_routes import router as configuraciones_router
from app.routes import actualizaciones_routes



app = FastAPI()


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)