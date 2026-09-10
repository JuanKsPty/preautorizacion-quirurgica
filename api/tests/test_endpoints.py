"""Las rutas de lectura y el camino sin IA."""

from fastapi.testclient import TestClient


def test_se_listan_las_polizas_sembradas(client: TestClient):
    polizas = client.get("/api/polizas").json()
    assert len(polizas) == 6
    assert {p["numero"] for p in polizas} >= {"POL-2024-0148", "POL-2026-0731"}


def test_se_listan_los_informes_con_su_relato(client: TestClient):
    informes = client.get("/api/informes").json()
    assert len(informes) == 8
    assert all(i["texto"] for i in informes), "un informe sin relato no sirve de nada"


def test_el_catalogo_publica_carencias_y_exclusiones(client: TestClient):
    """
    La pantalla de reglas lo muestra tal cual: es lo que permite comprobar que
    el dictamen se ajusta a la norma que estaba publicada de antemano.
    """
    catalogo = client.get("/api/procedimientos").json()
    assert len(catalogo) == 10
    colecistectomia = next(p for p in catalogo if p["cpt"] == "47562")
    assert colecistectomia["carencia_dias"] == {
        "basico": 180,
        "preferente": 90,
        "ejecutivo": 60,
    }
    liposuccion = next(p for p in catalogo if p["cpt"] == "15877")
    assert "estétic" in liposuccion["exclusion"]


def test_una_poliza_que_no_existe_da_404(client: TestClient):
    assert client.get("/api/polizas/POL-NO-EXISTE").status_code == 404


def test_el_motor_de_reglas_resuelve_sin_ia(client: TestClient):
    """El camino que garantiza un veredicto aunque el proveedor de IA no responda."""
    respuesta = client.post(
        "/api/preautorizaciones/reglas", json={"codigo_informe": "INF-2026-0031"}
    )
    assert respuesta.status_code == 200, respuesta.text
    dictamen = respuesta.json()
    assert dictamen["veredicto"] == "APROBADO"
    assert dictamen["cpt_identificado"] == "47562"
    assert dictamen["folio"] == "PA-2026-0031"
    assert len(dictamen["chequeos"]) == 6


def test_el_motor_de_reglas_tambien_rechaza_cuando_toca(client: TestClient):
    dictamen = client.post(
        "/api/preautorizaciones/reglas", json={"codigo_informe": "INF-2026-0038"}
    ).json()
    assert dictamen["veredicto"] == "RECHAZADO"
    assert "primas pendientes" in dictamen["motivos"][0].lower()


def test_la_sonda_de_streaming_emite_los_cinco_pasos(client: TestClient):
    respuesta = client.get("/api/diagnostico/sse")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    assert respuesta.text.count("data:") == 6  # 5 pasos + fin
