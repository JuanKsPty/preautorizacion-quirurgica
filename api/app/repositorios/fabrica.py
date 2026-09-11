"""
Eleccion del repositorio.

Lectura y escritura se resuelven por caminos distintos a proposito:

  * La LECTURA usa Notion envuelto en `RepositorioConRespaldo`, o los datos de
    demostracion si no hay token. Un token configurado no garantiza acceso —la
    integracion puede no estar conectada a las paginas— y ese caso tiene que
    degradar, no devolver un 500.

  * La ESCRITURA usa Notion a pelo, o no hay escritura. No existe un respaldo
    donde escribir, y guardar en un sitio que se pierde al reiniciar seria peor
    que no guardar: la persona se va creyendo que su registro existe.
"""

import logging

from app.core.config import settings
from app.repositorios.base import RepositorioClinico
from app.repositorios.demo import RepositorioDemo
from app.repositorios.notion import NotionRepositorio
from app.repositorios.respaldo import RepositorioConRespaldo

logger = logging.getLogger("app.repositorios")

_repositorio: RepositorioClinico | None = None
_notion: NotionRepositorio | None = None


class NotionNoConfigurado(RuntimeError):
    """Se pidio escribir y no hay Notion. Para escribir no hay plan B."""


def obtener_repositorio() -> RepositorioClinico:
    """Un solo repositorio por proceso: la cache de data sources se reutiliza."""
    global _repositorio, _notion
    if _repositorio is None:
        if settings.notion_habilitado:
            logger.info("Origen de datos: Notion (con respaldo local en lectura)")
            _notion = NotionRepositorio()
            _repositorio = RepositorioConRespaldo(_notion, RepositorioDemo())
        else:
            logger.info("Origen de datos: demostración (sin NOTION_TOKEN)")
            _repositorio = RepositorioDemo()
    return _repositorio


def obtener_repositorio_escritura() -> NotionRepositorio:
    """
    El repositorio que sabe escribir, sin la red de seguridad de la lectura.

    Devuelve la MISMA instancia que usa la lectura: si no, la primera escritura
    pagaria un `databases.retrieve` extra por cada base para rellenar su propia
    cache de data sources.
    """
    obtener_repositorio()  # fuerza la construccion del singleton
    if _notion is None:
        raise NotionNoConfigurado(
            "La creación y edición de registros requiere Notion. Configura "
            "NOTION_TOKEN y los identificadores NOTION_DB_*. La lectura sigue "
            "funcionando con los datos de demostración; la escritura no tiene "
            "respaldo a propósito."
        )
    return _notion


def escritura_disponible() -> bool:
    """Lo consulta /api/health para que la interfaz pueda deshabilitar el alta."""
    return settings.notion_habilitado


def notificar_escritura_exitosa() -> None:
    """
    Una escritura correcta demuestra que Notion responde: reabre la lectura.

    Sin esto, si la lectura se degrado hace 40 segundos, el registro recien
    creado NO aparece en la lista durante los 20 restantes — y delante de
    alguien eso se lee como "no se guardó".
    """
    repositorio = obtener_repositorio()
    if isinstance(repositorio, RepositorioConRespaldo) and repositorio.degradado:
        logger.info("Escritura correcta en Notion: se reanuda la lectura real.")
        repositorio.reintentar_primario()


def estado_origen() -> tuple[str, str | None]:
    """(origen real, motivo de la degradacion si la hay). Lo usa /api/health."""
    repositorio = obtener_repositorio()
    if isinstance(repositorio, RepositorioConRespaldo):
        return repositorio.origen, repositorio.ultimo_error
    return repositorio.origen, None


def reiniciar_repositorio() -> None:
    """Solo para pruebas: fuerza a releer la configuracion."""
    global _repositorio, _notion
    _repositorio = None
    # Limpiar tambien este: si no, una prueba que reinicie el repositorio se
    # quedaria con el Notion de la anterior y el fallo seria desconcertante.
    _notion = None
