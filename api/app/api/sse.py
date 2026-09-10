"""
Utilidades de Server-Sent Events.

Las cabeceras no son decorativas: sin `X-Accel-Buffering: no` nginx acumula la
respuesta en su buffer y el stream se ve congelado, que es el modo de fallo mas
comun de un SSE detras de un proxy. `Connection: keep-alive` se omite a
proposito: es una cabecera hop-by-hop, no significa nada sobre HTTP/2 y HTTP/3,
y los proxies la descartan.
"""

import json
from typing import Any

CABECERAS_SSE = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


def evento(payload: dict[str, Any]) -> str:
    """Un evento SSE: `data: {...}` y una linea en blanco que lo cierra."""
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def latido() -> str:
    """
    Comentario SSE. Mantiene la conexion viva sin ensuciar el flujo de datos:
    un cliente que trocea por lineas `data:` lo ignora solo.
    """
    return ": latido\n\n"
