"""
El respaldo en tiempo de ejecucion.

Esta prueba existe por un fallo real en produccion: con NOTION_TOKEN puesto pero
la integracion sin conectar a las paginas, Notion devuelve "Could not find
database ... Make sure the relevant pages and databases are shared with your
integration" y TODAS las peticiones respondian 500.

Tener token configurado no es lo mismo que tener acceso. El respaldo tiene que
cubrir el fallo al usarlo, no solo su ausencia en el arranque.
"""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from notion_client.errors import APIResponseError

from app.repositorios.demo import RepositorioDemo
from app.repositorios.respaldo import RepositorioConRespaldo


class _NotionCaido:
    """Un Notion que rechaza todo, como cuando la integracion no esta conectada."""

    def __init__(self) -> None:
        self.intentos = 0

    @property
    def origen(self) -> str:
        return "notion"

    def _reventar(self):
        self.intentos += 1
        # El error exacto que devuelve Notion cuando la integracion existe
        # pero no esta conectada a las paginas.
        raise APIResponseError(
            code="object_not_found",
            status=404,
            message=(
                "Could not find database with ID: c630c72a. Make sure the relevant "
                'pages and databases are shared with your integration "api".'
            ),
            headers=httpx.Headers(),
            raw_body_text="{}",
        )

    async def listar_polizas(self):
        self._reventar()

    async def obtener_poliza(self, numero):
        self._reventar()

    async def listar_informes(self):
        self._reventar()

    async def obtener_informe(self, codigo):
        self._reventar()

    async def listar_procedimientos(self):
        self._reventar()

    async def registrar_dictamen(self, dictamen):
        self._reventar()


@pytest.fixture(name="con_respaldo")
def con_respaldo_fixture() -> RepositorioConRespaldo:
    return RepositorioConRespaldo(_NotionCaido(), RepositorioDemo())


def test_si_notion_falla_se_sirven_los_datos_locales(con_respaldo):
    polizas = asyncio.run(con_respaldo.listar_polizas())
    assert len(polizas) == 6, "deberia haber caido al respaldo, no propagar el error"
    assert con_respaldo.degradado is True
    assert con_respaldo.origen == "demo"


def test_el_motivo_de_la_degradacion_queda_a_la_vista(con_respaldo):
    """Sin esto, un despliegue degradado es un misterio desde fuera."""
    asyncio.run(con_respaldo.listar_polizas())
    assert con_respaldo.ultimo_error is not None
    assert "shared with your integration" in con_respaldo.ultimo_error


def test_no_se_reintenta_notion_en_cada_peticion(con_respaldo):
    """Una vez degradado, no se castiga cada peticion con un viaje que va a fallar."""
    caido = con_respaldo._primario
    for _ in range(5):
        asyncio.run(con_respaldo.listar_polizas())
    assert caido.intentos == 1


def test_pasada_la_espera_se_vuelve_a_probar_notion(con_respaldo, monkeypatch):
    """
    Sin esta reapertura, conectar la integracion en Notion no surtiria efecto
    hasta redesplegar — y nadie relacionaria una cosa con la otra.
    """
    caido = con_respaldo._primario
    asyncio.run(con_respaldo.listar_polizas())
    assert caido.intentos == 1

    # Se simula que paso el tiempo de espera.
    monkeypatch.setattr(type(con_respaldo), "ESPERA_REINTENTO", 0.0)
    asyncio.run(con_respaldo.listar_polizas())
    assert caido.intentos == 2, "deberia haber reintentado el primario"


def test_se_puede_rehabilitar_notion_sin_reiniciar(con_respaldo):
    asyncio.run(con_respaldo.listar_polizas())
    con_respaldo.reintentar_primario()
    assert con_respaldo.degradado is False
    asyncio.run(con_respaldo.listar_polizas())
    assert con_respaldo._primario.intentos == 2


def test_un_fallo_de_escritura_no_degrada_la_lectura():
    """
    Que no se pueda escribir el dictamen en Notion no dice nada sobre si se
    puede leer: son permisos distintos y bases distintas.
    """
    repositorio = RepositorioConRespaldo(_NotionCaido(), RepositorioDemo())
    from app.dominio.esquemas import Dictamen

    dictamen = Dictamen(
        folio="PA-TEST",
        veredicto="APROBADO",
        resumen="x",
        numero_poliza="POL-2024-0148",
        codigo_informe="INF-2026-0031",
        paciente="Prueba",
    )
    assert asyncio.run(repositorio.registrar_dictamen(dictamen)) is None
    assert repositorio.degradado is False


def test_los_endpoints_responden_200_con_notion_caido(client: TestClient, monkeypatch):
    """La comprobacion que importa: la API no devuelve 500 por culpa de Notion."""
    from app.repositorios import fabrica

    monkeypatch.setattr(
        fabrica, "_repositorio", RepositorioConRespaldo(_NotionCaido(), RepositorioDemo())
    )

    assert client.get("/api/polizas").status_code == 200
    assert len(client.get("/api/informes").json()) == 8
    assert client.get("/api/procedimientos").status_code == 200

    salud = client.get("/api/health").json()
    assert salud["origen_datos"] == "demo"
    assert salud["notion_error"] is not None

    # Y se sigue pudiendo emitir un dictamen.
    dictamen = client.post(
        "/api/preautorizaciones/reglas", json={"codigo_informe": "INF-2026-0031"}
    ).json()
    assert dictamen["veredicto"] == "APROBADO"
