from fastapi.testclient import TestClient


def test_registro_devuelve_token(client: TestClient) -> None:
    respuesta = client.post(
        "/api/auth/register",
        json={"email": "nuevo@demo.com", "password": "password123"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["token_type"] == "bearer"
    assert respuesta.json()["access_token"]


def test_no_permite_dos_cuentas_con_el_mismo_correo(client: TestClient) -> None:
    datos = {"email": "repetido@demo.com", "password": "password123"}
    client.post("/api/auth/register", json=datos)

    respuesta = client.post("/api/auth/register", json=datos)

    assert respuesta.status_code == 409
    assert "correo" in respuesta.json()["detail"]


def test_rechaza_password_corta(client: TestClient) -> None:
    respuesta = client.post(
        "/api/auth/register",
        json={"email": "corta@demo.com", "password": "1234"},
    )

    assert respuesta.status_code == 422


def test_login_con_credenciales_correctas(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "login@demo.com", "password": "password123"},
    )

    respuesta = client.post(
        "/api/auth/login",
        json={"email": "login@demo.com", "password": "password123"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]


def test_login_con_password_incorrecta(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "malo@demo.com", "password": "password123"},
    )

    respuesta = client.post(
        "/api/auth/login",
        json={"email": "malo@demo.com", "password": "otra-password"},
    )

    assert respuesta.status_code == 401


def test_me_requiere_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_devuelve_el_usuario_sin_el_hash(client: TestClient, auth: dict[str, str]) -> None:
    respuesta = client.get("/api/auth/me", headers=auth)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "tester@demo.com"
    assert "hashed_password" not in cuerpo
    # La fecha debe llevar zona horaria para que el frontend no la corra.
    assert cuerpo["created_at"].endswith("+00:00")


def test_token_invalido_da_401(client: TestClient) -> None:
    respuesta = client.get("/api/auth/me", headers={"Authorization": "Bearer no-es-un-token"})

    assert respuesta.status_code == 401
