from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import SessionDep
from app.repositorios.fabrica import estado_origen

router = APIRouter(tags=["sistema"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: str
    ia_habilitada: bool
    modelo: str
    esfuerzo: str
    origen_datos: str
    notion_habilitado: bool
    # Por que se esta leyendo del respaldo aunque Notion este configurado.
    notion_error: str | None = None


@router.get("/health", response_model=HealthResponse, summary="Estado de la API")
def health(session: SessionDep) -> HealthResponse:
    """
    Lo consulta el panel del frontend y sirve para verificar la configuracion
    del despliegue desde fuera, sin entrar al servidor: dice si la base responde,
    si hay clave de IA y si esta leyendo de Notion o de los datos de demostracion.
    """
    try:
        session.exec(text("SELECT 1"))  # type: ignore[call-overload]
        base_de_datos = f"{settings.database_kind} (conectada)"
        estado = "ok"
    except Exception:  # cualquier fallo de conexion cuenta como degradado
        base_de_datos = f"{settings.database_kind} (sin conexion)"
        estado = "degraded"

    origen, motivo = estado_origen()

    return HealthResponse(
        status=estado,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database=base_de_datos,
        ia_habilitada=settings.ia_habilitada,
        modelo=settings.anthropic_model,
        esfuerzo=settings.anthropic_effort,
        origen_datos=origen,
        notion_habilitado=settings.notion_habilitado,
        notion_error=motivo,
    )
