import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_chat_requiere_sesion(client: TestClient) -> None:
    respuesta = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hola"}]})

    assert respuesta.status_code == 401


def test_chat_sin_api_key_avisa_con_503(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Independiente de si el .env local tiene clave configurada.
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    respuesta = client.post(
        "/api/chat",
        headers=auth,
        json={"messages": [{"role": "user", "content": "hola"}]},
    )

    assert respuesta.status_code == 503
    assert "ANTHROPIC_API_KEY" in respuesta.json()["detail"]


def test_chat_valida_el_rol_de_los_mensajes(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")

    respuesta = client.post(
        "/api/chat",
        headers=auth,
        json={"messages": [{"role": "sistema", "content": "hola"}]},
    )

    assert respuesta.status_code == 422
