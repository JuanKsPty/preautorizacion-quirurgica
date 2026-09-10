import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.db.session import create_db_and_tables

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        try:
            create_db_and_tables()
            logger.info("Tablas verificadas en %s", settings.database_kind)
        except Exception:
            # La API arranca igual: /api/health dira que la base no responde,
            # que es mas util que un crash al inicio en medio de una demo.
            logger.exception("No se pudieron crear las tablas")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    summary="API del proyecto. Todo cuelga de /api.",
    lifespan=lifespan,
    # Bajo /api para que el proxy de Vite y el de nginx las sirvan sin reglas extra.
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def error_no_previsto(request: Request, exc: Exception) -> JSONResponse:
    """Cualquier excepcion sin manejar sale como JSON, no como HTML de error."""
    logger.exception("Error no manejado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Revisa los logs de la API."},
    )


app.include_router(api_router, prefix="/api")
