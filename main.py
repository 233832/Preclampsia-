from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared.config.database import engine, Base
from app.routes.paciente_routes import paciente_router
from app.routes.expediente_routes import expediente_router
from app.routes.consulta_routes import consulta_router

app = FastAPI()

app.include_router(paciente_router, prefix="/api", tags=["pacientes"])
app.include_router(expediente_router, prefix="/api", tags=["expedientes"])
app.include_router(consulta_router, prefix="/api", tags=["consultas"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)