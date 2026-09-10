import json
from collections.abc import AsyncGenerator
from typing import Literal

import anthropic
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import CurrentUser

router = APIRouter(prefix="/chat", tags=["ia"])

PROMPT_SISTEMA = (
    "Eres el asistente de una aplicacion web. Responde en espanol, de forma "
    "breve y concreta. Si no sabes algo, dilo en lugar de inventarlo."
)


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=40)
    # Opcional: permite al frontend especializar el asistente por pantalla.
    system: str | None = Field(default=None, max_length=2000)


_cliente: anthropic.AsyncAnthropic | None = None


def _obtener_cliente() -> anthropic.AsyncAnthropic:
    """Un solo cliente para toda la app: reutiliza el pool de conexiones."""
    global _cliente
    if _cliente is None:
        _cliente = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _cliente


def _evento(payload: dict) -> str:
    """Formatea un evento SSE: 'data: {...}' y una linea en blanco al final."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("", summary="Chat con el modelo, respuesta en streaming (SSE)")
async def chat(peticion: ChatRequest, usuario: CurrentUser) -> StreamingResponse:
    """
    Devuelve la respuesta del modelo por Server-Sent Events, para que el
    frontend la muestre token por token en vez de esperar el parrafo completo.

    Eventos que emite:
      {"type": "delta", "text": "..."}   fragmento de texto
      {"type": "done"}                   termino bien
      {"type": "error", "message": "..."} fallo a mitad del stream
    """
    if not settings.ai_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El chat necesita ANTHROPIC_API_KEY en el .env de la raiz del proyecto",
        )

    cliente = _obtener_cliente()
    mensajes = [{"role": mensaje.role, "content": mensaje.content} for mensaje in peticion.messages]

    async def generar() -> AsyncGenerator[str]:
        try:
            async with cliente.messages.stream(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=peticion.system or PROMPT_SISTEMA,
                messages=mensajes,  # type: ignore[arg-type]
            ) as stream:
                async for fragmento in stream.text_stream:
                    yield _evento({"type": "delta", "text": fragmento})
            yield _evento({"type": "done"})
        except anthropic.APIStatusError as error:
            # Una vez empezado el stream ya no podemos cambiar el status HTTP,
            # asi que el error viaja como un evento mas.
            yield _evento(
                {
                    "type": "error",
                    "message": f"El proveedor de IA respondio con codigo {error.status_code}",
                }
            )
        except anthropic.APIConnectionError:
            yield _evento(
                {"type": "error", "message": "No se pudo conectar con el proveedor de IA"}
            )

    return StreamingResponse(
        generar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Sin esto, nginx bufferea la respuesta y el chat parece congelado.
            "X-Accel-Buffering": "no",
        },
    )
