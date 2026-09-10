"""
Sonda de streaming.

Emite cinco eventos separados por un segundo. Existe para poder demostrar que
el camino completo (Traefik -> uvicorn -> navegador) transmite por goteo y no
de golpe, sin depender de que haya clave de IA ni datos cargados. Cuando un
stream "se ve congelado" en el despliegue, esta es la primera pieza que se
descarta.
"""

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import CABECERAS_SSE, evento

router = APIRouter(prefix="/diagnostico", tags=["sistema"])


@router.get("/sse", summary="Sonda de streaming (5 eventos, 1 por segundo)")
async def sonda_sse() -> StreamingResponse:
    async def generar() -> AsyncGenerator[str]:
        for paso in range(1, 6):
            yield evento({"tipo": "paso", "numero": paso, "de": 5})
            await asyncio.sleep(1)
        yield evento({"tipo": "fin"})

    return StreamingResponse(generar(), media_type="text/event-stream", headers=CABECERAS_SSE)
