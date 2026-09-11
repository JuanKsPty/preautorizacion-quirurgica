"""
Los endpoints de alta y edición.

La prueba central es `test_con_notion_caido_no_se_crea_y_NO_cae_al_demo`: es la
decisión de diseño escrita en código. Escribir no tiene respaldo, y guardar en
un sitio que se pierde al reiniciar sería peor que no guardar — quien lo hizo se
marcharía creyendo que su registro existe.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.deps import exigir_repositorio_escritura
from app.main import app
from app.repositorios.datos_demo import INFORMES, POLIZAS

INFORME_VALIDO = {
    "paciente": "Marta Cedeño Ruiz",
    "cedula": "8-812-2043",
    "numero_poliza": "POL-2024-0148",
    "hospital": "Hospital Punta Pacífica",
    "medico_tratante": "Dra. Ileana Sáez Moreno",
    "especialidad": "Cirugía general",
    "fecha_informe": "2026-09-10",
    "fecha_cirugia_propuesta": "2026-09-25",
    "es_emergencia": False,
    "monto_cotizado": 6800.0,
    "documentos_adjuntos": ["Informe médico firmado", "Copia de cédula"],
    "texto": (
        "Paciente femenina de 44 años con cuadro de tres meses de dolor en "
        "hipocondrio derecho, de tipo cólico, desencadenado por comidas grasas. "
        "Ultrasonido con múltiples litos en vesícula. Se indica extirpación de la "
        "vesícula biliar por vía laparoscópica de forma electiva."
    ),
}

POLIZA_VALIDA = {
    "titular": "Marta Cedeño Ruiz",
    "cedula": "8-999-1111",
    "plan": "preferente",
    "estado": "vigente",
    "inicio_vigencia": "2026-01-01",
    "fin_vigencia": "2029-01-01",
    "deducible_anual": 500.0,
    "deducible_consumido": 0.0,
    "coaseguro_porcentaje": 20,
    "tope_anual": 50000.0,
    "tope_consumido": 0.0,
    "red_preferente": True,
    "preexistencias_declaradas": [],
    "dependientes": [],
}


class _EscrituraFalsa:
    """Notion que funciona. Registra lo que se le pide."""

    def __init__(self) -> None:
        import asyncio

        self.candado_escritura = asyncio.Lock()
        self.creados: list = []
        self.editados: list = []
        self.codigos_existentes: set[str] = set()
        self.polizas = {p.numero: p for p in POLIZAS}

    async def obtener_poliza(self, numero):
        return self.polizas.get(numero.strip())

    async def existe_informe(self, codigo):
        return codigo in self.codigos_existentes

    async def existe_poliza(self, numero):
        return numero in self.polizas

    async def siguiente_codigo_informe(self, anio):
        return f"INF-{anio}-0099"

    async def siguiente_numero_poliza(self, anio):
        return f"POL-{anio}-0099"

    async def crear_informe(self, informe):
        self.creados.append(informe)
        return "https://notion.so/informe-nuevo"

    async def crear_poliza(self, poliza):
        self.creados.append(poliza)
        return "https://notion.so/poliza-nueva"

    async def actualizar_informe(self, codigo, informe):
        from app.repositorios.notion import RegistroNoEncontrado

        if codigo not in self.codigos_existentes:
            raise RegistroNoEncontrado(f"No existe el informe {codigo}")
        self.editados.append(informe)
        return "https://notion.so/informe-editado"

    async def actualizar_poliza(self, numero, poliza):
        from app.repositorios.notion import RegistroNoEncontrado

        if numero not in self.polizas:
            raise RegistroNoEncontrado(f"No existe la póliza {numero}")
        self.editados.append(poliza)
        return "https://notion.so/poliza-editada"


class _EscrituraCaida(_EscrituraFalsa):
    """Notion que acepta la consulta previa pero revienta al escribir."""

    async def crear_informe(self, informe):
        raise _ErrorNotion("unauthorized")

    async def crear_poliza(self, poliza):
        raise _ErrorNotion("unauthorized")


class _ErrorNotion(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(f"Notion dijo que no: {code}")
        self.code = code


@pytest.fixture(name="escritura")
def escritura_fixture(client: TestClient):
    falsa = _EscrituraFalsa()
    app.dependency_overrides[exigir_repositorio_escritura] = lambda: falsa
    yield falsa
    app.dependency_overrides.pop(exigir_repositorio_escritura, None)


# ------------------------------------------------------ sin Notion no se escribe


def test_sin_notion_configurado_no_se_puede_crear(client: TestClient, monkeypatch):
    from app.core.config import settings
    from app.repositorios import fabrica

    monkeypatch.setattr(settings, "notion_token", "")
    fabrica.reiniciar_repositorio()

    respuesta = client.post("/api/informes", json=INFORME_VALIDO)
    assert respuesta.status_code == 503
    detalle = respuesta.json()["detail"]
    assert "NOTION_TOKEN" in detalle
    # Y el mensaje tiene que dejar claro que la aplicación no está rota.
    assert "lectura sigue funcionando" in detalle
    fabrica.reiniciar_repositorio()


def test_con_notion_caido_no_se_crea_y_NO_cae_al_demo(client: TestClient):
    """
    La decisión de diseño, escrita en código: la escritura no tiene respaldo.

    Y a la vez, la LECTURA sigue sirviendo desde los datos locales — las dos
    mitades se comportan distinto a propósito.
    """
    app.dependency_overrides[exigir_repositorio_escritura] = lambda: _EscrituraCaida()
    try:
        respuesta = client.post("/api/informes", json=INFORME_VALIDO)
        assert respuesta.status_code == 503
        assert "permisos" in respuesta.json()["detail"]

        # La lectura no se ha visto afectada.
        assert len(client.get("/api/informes").json()) == len(INFORMES)
    finally:
        app.dependency_overrides.pop(exigir_repositorio_escritura, None)


# --------------------------------------------------------------------- alta


def test_crear_un_informe_devuelve_la_url_de_notion(client: TestClient, escritura):
    respuesta = client.post("/api/informes", json=INFORME_VALIDO)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["notion_url"] == "https://notion.so/informe-nuevo"
    assert cuerpo["informe"]["codigo"] == "INF-2026-0099"
    assert respuesta.headers["Location"] == "/api/informes/INF-2026-0099"
    assert len(escritura.creados) == 1


def test_un_codigo_repetido_da_409_y_no_crea_nada(client: TestClient, escritura):
    escritura.codigos_existentes.add("INF-2026-0031")
    respuesta = client.post("/api/informes", json={**INFORME_VALIDO, "codigo": "INF-2026-0031"})
    assert respuesta.status_code == 409
    assert escritura.creados == []


def test_crear_una_poliza(client: TestClient, escritura):
    respuesta = client.post("/api/polizas", json=POLIZA_VALIDA)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["poliza"]["numero"] == "POL-2026-0099"


# ------------------------------------------------------------------ edicion


def test_editar_un_informe_que_no_existe_da_404(client: TestClient, escritura):
    respuesta = client.put("/api/informes/INF-2026-9999", json=INFORME_VALIDO)
    assert respuesta.status_code == 404


def test_editar_un_informe_existente(client: TestClient, escritura):
    escritura.codigos_existentes.add("INF-2026-0031")
    respuesta = client.put("/api/informes/INF-2026-0031", json=INFORME_VALIDO)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["informe"]["codigo"] == "INF-2026-0031"


# --------------------------------------------------------------- validacion


def test_la_cirugia_no_puede_ser_anterior_al_informe(client: TestClient, escritura):
    respuesta = client.post(
        "/api/informes",
        json={**INFORME_VALIDO, "fecha_cirugia_propuesta": "2026-09-01"},
    )
    assert respuesta.status_code == 422
    assert "anterior" in respuesta.json()["detail"]


def test_una_fecha_de_cirugia_a_dos_siglos_se_rechaza(client: TestClient, escritura):
    """El 2206 tecleado por 2026 atravesaría todas las reglas sin protestar."""
    respuesta = client.post(
        "/api/informes",
        json={**INFORME_VALIDO, "fecha_cirugia_propuesta": "2206-09-25"},
    )
    assert respuesta.status_code == 422
    assert "dos años" in respuesta.json()["detail"]


def test_una_poliza_inexistente_se_rechaza(client: TestClient, escritura):
    respuesta = client.post(
        "/api/informes", json={**INFORME_VALIDO, "numero_poliza": "POL-2099-0001"}
    )
    assert respuesta.status_code == 422
    assert "no existe" in respuesta.json()["detail"]


def test_un_monto_de_cero_se_rechaza(client: TestClient, escritura):
    respuesta = client.post("/api/informes", json={**INFORME_VALIDO, "monto_cotizado": 0})
    assert respuesta.status_code == 422


def test_un_relato_demasiado_corto_se_rechaza(client: TestClient, escritura):
    """Por debajo del mínimo, el emparejador no puede identificar el procedimiento."""
    respuesta = client.post("/api/informes", json={**INFORME_VALIDO, "texto": "Duele."})
    assert respuesta.status_code == 422


def test_un_estado_de_poliza_inventado_se_rechaza(client: TestClient, escritura):
    """
    No es cosmético: `_a_poliza` pasa el estado tal cual al Literal sin defecto,
    así que un valor inventado haría que `listar_polizas()` lanzara y degradara
    la aplicación entera durante 60 segundos.
    """
    respuesta = client.post("/api/polizas", json={**POLIZA_VALIDA, "estado": "En mora"})
    assert respuesta.status_code == 422


def test_un_deducible_consumido_mayor_que_el_anual_se_rechaza(client: TestClient, escritura):
    respuesta = client.post("/api/polizas", json={**POLIZA_VALIDA, "deducible_consumido": 900.0})
    assert respuesta.status_code == 422
    assert "deducible" in respuesta.json()["detail"]


def test_un_punto_y_coma_en_un_dependiente_se_rechaza(client: TestClient, escritura):
    """Es el separador con el que se guardan: partiría el nombre en dos."""
    respuesta = client.post("/api/polizas", json={**POLIZA_VALIDA, "dependientes": ["Pérez; Juan"]})
    assert respuesta.status_code == 422


def test_la_vigencia_tiene_que_avanzar(client: TestClient, escritura):
    respuesta = client.post("/api/polizas", json={**POLIZA_VALIDA, "fin_vigencia": "2025-01-01"})
    assert respuesta.status_code == 422


# ---------------------------------------------------- documentos y avisos


def test_un_documento_sin_tilde_se_ajusta_a_la_grafia_del_catalogo(client: TestClient, escritura):
    """
    El fallo más confuso de toda la app: `evaluar_documentos` compara cadenas
    normalizadas, así que «Estudio de imagenes» sin tilde produce
    DOCUMENTOS_FALTANTES sin ningún error a la vista. Se corrige al guardar.
    """
    respuesta = client.post(
        "/api/informes",
        json={**INFORME_VALIDO, "documentos_adjuntos": ["estudio de imagenes"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["informe"]["documentos_adjuntos"] == ["Estudio de imágenes"]
    assert any("se guardó como" in a for a in cuerpo["avisos"])


def test_un_documento_desconocido_se_guarda_con_aviso(client: TestClient, escritura):
    respuesta = client.post(
        "/api/informes",
        json={**INFORME_VALIDO, "documentos_adjuntos": ["Carta del abuelo"]},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["informe"]["documentos_adjuntos"] == ["Carta del abuelo"]
    assert any("no está en el catálogo" in a for a in cuerpo["avisos"])


def test_una_cedula_que_no_casa_avisa_pero_no_bloquea(client: TestClient, escritura):
    """La demostración tiene que poder crear un caso equivocado a propósito."""
    respuesta = client.post("/api/informes", json={**INFORME_VALIDO, "cedula": "9-999-9999"})
    assert respuesta.status_code == 201
    assert any("no coincide" in a for a in respuesta.json()["avisos"])


def test_una_fecha_de_informe_en_el_futuro_avisa(client: TestClient, escritura):
    futuro = (date.today() + timedelta(days=30)).isoformat()
    respuesta = client.post(
        "/api/informes",
        json={
            **INFORME_VALIDO,
            "fecha_informe": futuro,
            "fecha_cirugia_propuesta": (date.today() + timedelta(days=60)).isoformat(),
        },
    )
    assert respuesta.status_code == 201
    assert any("futuro" in a for a in respuesta.json()["avisos"])


def test_tras_escribir_se_reabre_la_lectura_de_notion(client: TestClient, escritura):
    """
    Si la lectura se degradó hace 40 segundos, el registro recién creado no
    aparecería en la lista durante los 20 restantes — y delante de alguien eso
    se lee como «no se guardó». Una escritura correcta demuestra que Notion
    responde, así que reabre la lectura.
    """
    from app.repositorios import fabrica
    from app.repositorios.demo import RepositorioDemo
    from app.repositorios.respaldo import RepositorioConRespaldo

    from .test_respaldo import _NotionCaido

    degradado = RepositorioConRespaldo(_NotionCaido(), RepositorioDemo())
    import asyncio

    asyncio.run(degradado.listar_polizas())  # provoca la degradación
    assert degradado.degradado is True

    fabrica._repositorio = degradado
    try:
        assert client.post("/api/informes", json=INFORME_VALIDO).status_code == 201
        assert degradado.degradado is False, "la escritura correcta debía reabrir la lectura"
    finally:
        fabrica.reiniciar_repositorio()
