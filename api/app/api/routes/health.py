from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import SessionDep

router = APIRouter(tags=["sistema"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: str
    ai_enabled: bool


@router.get("/health", response_model=HealthResponse, summary="Estado de la API")
def health(session: SessionDep) -> HealthResponse:
    """
    Lo consulta la pantalla de inicio del frontend para demostrar en vivo que
    React y FastAPI se estan hablando.
    """
    try:
        session.exec(text("SELECT 1"))  # type: ignore[call-overload]
        base_de_datos = f"{settings.database_kind} (conectada)"
        estado = "ok"
    except Exception:  # cualquier fallo de conexion cuenta como degradado
        base_de_datos = f"{settings.database_kind} (sin conexion)"
        estado = "degraded"

    return HealthResponse(
        status=estado,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database=base_de_datos,
        ai_enabled=settings.ai_enabled,
    )
