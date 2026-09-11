"""
Traduccion de un fallo de Notion a una respuesta que le sirva a quien opera.

La regla es que una escritura NUNCA termine en 500. El manejador global de
`main.py` responde «Error interno del servidor. Revisa los logs de la API», que
delante de alguien es el peor mensaje posible: no dice que pasa, no dice que
hacer, y sugiere que el sistema esta roto cuando casi siempre lo que falta es un
permiso.

Se usa 503 —y no 502— para todo fallo de transporte o de permisos porque es el
estado que esta aplicacion ya usa para «una dependencia que necesito no
responde», y la interfaz ya lo distingue.
"""

from typing import Any

from fastapi import HTTPException, status

CODIGOS_DE_PERMISO = {"unauthorized", "restricted_resource"}


def _codigo(error: Exception) -> str:
    return str(getattr(error, "code", "") or "")


def _cabeceras_reintento(error: Exception) -> dict[str, str]:
    cabeceras: Any = getattr(error, "headers", None)
    espera = "5"
    if cabeceras is not None:
        try:
            espera = str(cabeceras.get("retry-after") or "5")
        except Exception:  # una cabecera rara no puede tumbar el manejo del error
            espera = "5"
    return {"Retry-After": espera}


def error_de_notion(error: Exception) -> HTTPException:
    """Convierte cualquier fallo de Notion en una respuesta accionable."""
    codigo = _codigo(error)

    if codigo in CODIGOS_DE_PERMISO:
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Notion rechazó la escritura por permisos. Comprueba que la integración "
            "esté conectada a la página que contiene las bases y que tenga permiso "
            f"de edición. Notion dijo: {error}",
        )

    if codigo == "object_not_found":
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Notion no encuentra la base de datos. Revisa las variables NOTION_DB_* "
            "y que la integración esté compartida con esas páginas. "
            f"Notion dijo: {error}",
        )

    if codigo == "rate_limited":
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Notion está limitando las peticiones. Espera unos segundos y vuelve a "
            "guardar. No se creó nada.",
            headers=_cabeceras_reintento(error),
        )

    if codigo == "validation_error":
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Notion rechazó los datos: {error}",
        )

    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        f"No se pudo escribir en Notion, y la escritura no tiene respaldo. {error}",
    )
