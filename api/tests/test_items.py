from fastapi.testclient import TestClient


def test_items_requiere_sesion(client: TestClient) -> None:
    assert client.get("/api/items").status_code == 401


def test_crud_completo(client: TestClient, auth: dict[str, str]) -> None:
    # crear
    creado = client.post(
        "/api/items",
        headers=auth,
        json={"title": "Primer item", "description": "de prueba"},
    )
    assert creado.status_code == 201
    item = creado.json()
    assert item["done"] is False
    assert item["created_at"].endswith("+00:00")

    # listar
    listado = client.get("/api/items", headers=auth)
    assert listado.status_code == 200
    assert [elemento["id"] for elemento in listado.json()] == [item["id"]]

    # actualizar solo un campo
    actualizado = client.patch(f"/api/items/{item['id']}", headers=auth, json={"done": True})
    assert actualizado.status_code == 200
    assert actualizado.json()["done"] is True
    assert actualizado.json()["title"] == "Primer item"

    # borrar
    assert client.delete(f"/api/items/{item['id']}", headers=auth).status_code == 204
    assert client.get("/api/items", headers=auth).json() == []


def test_titulo_demasiado_corto_no_pasa(client: TestClient, auth: dict[str, str]) -> None:
    respuesta = client.post("/api/items", headers=auth, json={"title": "ab"})

    assert respuesta.status_code == 422


def test_un_usuario_no_ve_ni_toca_los_items_de_otro(
    client: TestClient, auth: dict[str, str]
) -> None:
    ajeno = client.post("/api/items", headers=auth, json={"title": "Item ajeno"}).json()

    otro = client.post(
        "/api/auth/register",
        json={"email": "intruso@demo.com", "password": "password123"},
    ).json()
    headers_intruso = {"Authorization": f"Bearer {otro['access_token']}"}

    assert client.get("/api/items", headers=headers_intruso).json() == []
    assert client.get(f"/api/items/{ajeno['id']}", headers=headers_intruso).status_code == 404
    assert (
        client.patch(
            f"/api/items/{ajeno['id']}", headers=headers_intruso, json={"done": True}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/items/{ajeno['id']}", headers=headers_intruso).status_code == 404
