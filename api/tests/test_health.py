from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient) -> None:
    respuesta = client.get("/api/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    assert set(cuerpo) == {"status", "app", "version", "environment", "database", "ai_enabled"}


def test_openapi_publica_los_endpoints(client: TestClient) -> None:
    rutas = client.get("/api/openapi.json").json()["paths"]

    assert "/api/auth/login" in rutas
    assert "/api/items" in rutas
    assert "/api/chat" in rutas
