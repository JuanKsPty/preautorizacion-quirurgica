from fastapi import APIRouter

from app.api.routes import catalogo, diagnostico, health, preautorizaciones

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(diagnostico.router)
api_router.include_router(catalogo.router)
api_router.include_router(preautorizaciones.router)
