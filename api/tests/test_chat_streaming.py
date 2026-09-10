"""
Verifica el formato de los eventos SSE del chat sin llamar al proveedor de IA:
sustituimos el cliente por uno falso. Asi el contrato entre el endpoint y el
parser del frontend (web/src/services/chatService.ts) queda cubierto por tests.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes import chat as modulo_chat
from app.core.config import settings


class _StreamFalso:
    def __init__(self, fragmentos: list[str]) -> None:
        self._fragmentos = fragmentos

    async def __aenter__(self) -> "_StreamFalso":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    @property
    def text_stream(self):
        async def generador():
            for fragmento in self._fragmentos:
                yield fragmento

        return generador()


class _MensajesFalsos:
    def __init__(self, fragmentos: list[str]) -> None:
        self.fragmentos = fragmentos
        self.parametros: dict | None = None

    def stream(self, **kwargs: object) -> _StreamFalso:
        self.parametros = kwargs
        return _StreamFalso(self.fragmentos)


class _ClienteFalso:
    def __init__(self, fragmentos: list[str]) -> None:
        self.messages = _MensajesFalsos(fragmentos)


def _eventos(cuerpo: str) -> list[dict]:
    return [
        json.loads(linea.removeprefix("data:").strip())
        for linea in cuerpo.splitlines()
        if linea.startswith("data:")
    ]


def test_devuelve_los_fragmentos_como_eventos_sse(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    falso = _ClienteFalso(["Hola", ", ", "mundo"])
    monkeypatch.setattr(modulo_chat, "_obtener_cliente", lambda: falso)

    respuesta = client.post(
        "/api/chat",
        headers=auth,
        json={"messages": [{"role": "user", "content": "saluda"}]},
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    # Sin esto nginx bufferea el stream y el chat se ve congelado.
    assert respuesta.headers["x-accel-buffering"] == "no"

    eventos = _eventos(respuesta.text)
    assert eventos == [
        {"type": "delta", "text": "Hola"},
        {"type": "delta", "text": ", "},
        {"type": "delta", "text": "mundo"},
        {"type": "done"},
    ]
    # El texto completo se reconstruye concatenando los deltas.
    assert "".join(e["text"] for e in eventos if e["type"] == "delta") == "Hola, mundo"


def test_pasa_el_modelo_y_el_prompt_de_sistema(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    monkeypatch.setattr(settings, "anthropic_model", "claude-sonnet-5")
    falso = _ClienteFalso(["ok"])
    monkeypatch.setattr(modulo_chat, "_obtener_cliente", lambda: falso)

    client.post(
        "/api/chat",
        headers=auth,
        json={
            "messages": [{"role": "user", "content": "hola"}],
            "system": "Responde solo con una palabra.",
        },
    )

    parametros = falso.messages.parametros
    assert parametros is not None
    assert parametros["model"] == "claude-sonnet-5"
    assert parametros["system"] == "Responde solo con una palabra."
    assert parametros["messages"] == [{"role": "user", "content": "hola"}]
    assert parametros["max_tokens"] == settings.anthropic_max_tokens
