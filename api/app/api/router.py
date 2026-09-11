from fastapi import APIRouter

from app.api.routes import catalogo, diagnostico, extraccion, health, preautorizaciones

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(diagnostico.router)
# La extraccion va ANTES del catalogo: /informes/extraer tiene que ganarle a
# /informes/{codigo}, que si no se lo comeria como si «extraer» fuera un codigo.
api_router.include_router(extraccion.router)
api_router.include_router(catalogo.router)
api_router.include_router(preautorizaciones.router)
