"""
Eleccion del repositorio.

Con token de Notion se usa Notion, pero SIEMPRE envuelto en `RepositorioConRespaldo`:
un token configurado no garantiza acceso —la integracion puede no estar conectada a
las paginas— y ese caso tiene que degradar a los datos locales, no devolver un 500.
Sin token se usan directamente los datos de demostracion.

La degradacion es silenciosa para el usuario pero visible en /api/health y en el
evento de inicio de cada evaluacion, para que nunca haya duda de que fuente se
esta leyendo.
"""

import logging

from app.core.config import settings
from app.repositorios.base import RepositorioClinico
from app.repositorios.demo import RepositorioDemo
from app.repositorios.notion import NotionRepositorio
from app.repositorios.respaldo import RepositorioConRespaldo

logger = logging.getLogger("app.repositorios")

_repositorio: RepositorioClinico | None = None


def obtener_repositorio() -> RepositorioClinico:
    """Un solo repositorio por proceso: la cache de data sources se reutiliza."""
    global _repositorio
    if _repositorio is None:
        if settings.notion_habilitado:
            logger.info("Origen de datos: Notion (con respaldo local)")
            _repositorio = RepositorioConRespaldo(NotionRepositorio(), RepositorioDemo())
        else:
            logger.info("Origen de datos: demostración (sin NOTION_TOKEN)")
            _repositorio = RepositorioDemo()
    return _repositorio


def estado_origen() -> tuple[str, str | None]:
    """(origen real, motivo de la degradacion si la hay). Lo usa /api/health."""
    repositorio = obtener_repositorio()
    if isinstance(repositorio, RepositorioConRespaldo):
        return repositorio.origen, repositorio.ultimo_error
    return repositorio.origen, None


def reiniciar_repositorio() -> None:
    """Solo para pruebas: fuerza a releer la configuracion."""
    global _repositorio
    _repositorio = None
