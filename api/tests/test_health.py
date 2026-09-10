from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient):
    respuesta = client.get("/api/health")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    # El endpoint reporta el motor CONFIGURADO (el .env), no el que inyecta
    # la prueba; lo que se comprueba aqui es que la conexion responde.
    assert "(conectada)" in cuerpo["database"]
    # Lo que hace verificable la configuracion del despliegue desde fuera.
    assert cuerpo["origen_datos"] in {"notion", "demo"}
    assert isinstance(cuerpo["ia_habilitada"], bool)
    assert isinstance(cuerpo["notion_habilitado"], bool)
    assert cuerpo["modelo"]


def test_openapi_publica_los_endpoints(client: TestClient):
    rutas = client.get("/api/openapi.json").json()["paths"]
    for esperada in (
        "/api/health",
        "/api/polizas",
        "/api/informes",
        "/api/procedimientos",
        "/api/preautorizaciones",
        "/api/preautorizaciones/evaluar",
        "/api/preautorizaciones/reglas",
        "/api/diagnostico/sse",
    ):
        assert esperada in rutas, f"falta {esperada} en el OpenAPI"
