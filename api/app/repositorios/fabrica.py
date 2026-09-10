"""
Eleccion del repositorio.

Con token de Notion y los identificadores de base configurados se usa Notion;
si no, los datos de demostracion. La caida a demo es silenciosa para el usuario
pero visible en /api/health y en el evento de inicio de cada evaluacion, para
que nunca haya duda de que fuente se esta leyendo.
"""

import logging

from app.core.config import settings
from app.repositorios.base import RepositorioClinico
from app.repositorios.demo import RepositorioDemo
from app.repositorios.notion import NotionRepositorio

logger = logging.getLogger("app.repositorios")

_repositorio: RepositorioClinico | None = None


def obtener_repositorio() -> RepositorioClinico:
    """Un solo repositorio por proceso: la cache de data sources se reutiliza."""
    global _repositorio
    if _repositorio is None:
        if settings.notion_habilitado:
            logger.info("Origen de datos: Notion")
            _repositorio = NotionRepositorio()
        else:
            logger.info("Origen de datos: demostración (sin NOTION_TOKEN)")
            _repositorio = RepositorioDemo()
    return _repositorio


def reiniciar_repositorio() -> None:
    """Solo para pruebas: fuerza a releer la configuracion."""
    global _repositorio
    _repositorio = None
