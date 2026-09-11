"""
El camino de escritura contra Notion, con un cliente falso.

El falso no imita la API entera: solo lo que el repositorio toca, y guarda lo
que le mandan para poder afirmarlo. `NotionRepositorio.__init__` ya acepta un
cliente inyectado, asi que no hace falta ninguna costura nueva ni parchear httpx.
"""

import asyncio
from typing import Any

import pytest

from app.core.config import settings
from app.repositorios.datos_demo import INFORMES, POLIZAS
from app.repositorios.escritura import parrafos, propiedades_poliza
from app.repositorios.notion import RegistroNoEncontrado

from .test_escritura import como_lo_devuelve_notion  # reutiliza la asimetria ya modelada


def fila_de(codigo: str, columna: str, page_id: str = "pag-1") -> dict[str, Any]:
    return {
        "id": page_id,
        "properties": {columna: {"title": [{"plain_text": codigo}]}},
    }


class _NotionFalso:
    """Registra cada peticion para poder afirmar sobre ella."""

    def __init__(self, filas: list[dict[str, Any]] | None = None) -> None:
        self.filas = filas or []
        self.creadas: list[dict[str, Any]] = []
        self.actualizadas: list[dict[str, Any]] = []
        self.consultas: list[dict[str, Any]] = []
        self.anexados: list[list[dict[str, Any]]] = []
        self.borrados: list[str] = []
        self.rechazar_erase = False
        falso = self

        class _Databases:
            async def retrieve(self, database_id: str, **_):
                return {"data_sources": [{"id": f"ds-{database_id}"}]}

        class _DataSources:
            async def query(self, **kwargs):
                falso.consultas.append(kwargs)
                return {"results": list(falso.filas), "has_more": False}

        class _Pages:
            async def create(self, **kwargs):
                falso.creadas.append(kwargs)
                return {"id": "pag-nueva", "url": "https://notion.so/pag-nueva"}

            async def update(self, **kwargs):
                if kwargs.get("erase_content") and falso.rechazar_erase:
                    raise ValueError("erase_content no soportado")
                falso.actualizadas.append(kwargs)
                return {"id": kwargs["page_id"], "url": "https://notion.so/editada"}

        class _Children:
            async def append(self, block_id: str, children: list, **_):
                falso.anexados.append(children)
                return {}

            async def list(self, block_id: str, **_):
                return {
                    "results": [{"id": "bloque-viejo-1"}, {"id": "bloque-viejo-2"}],
                    "has_more": False,
                }

        class _Blocks:
            children = _Children()

            async def delete(self, block_id: str, **_):
                falso.borrados.append(block_id)
                return {}

        self.databases = _Databases()
        self.data_sources = _DataSources()
        self.pages = _Pages()
        self.blocks = _Blocks()


def repositorio(falso: _NotionFalso):
    from app.repositorios.notion import NotionRepositorio

    return NotionRepositorio(cliente=falso)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _con_bases_configuradas(monkeypatch):
    """Los metodos leen settings.notion_db_*; sin esto irian a cadena vacia."""
    for campo in (
        "notion_db_polizas",
        "notion_db_informes",
        "notion_db_procedimientos",
    ):
        monkeypatch.setattr(settings, campo, f"db-{campo}")


# ------------------------------------------------------------------- alta


def test_crear_informe_manda_las_propiedades_y_el_relato_aparte():
    falso = _NotionFalso()
    informe = INFORMES[0]
    url = asyncio.run(repositorio(falso).crear_informe(informe))

    assert url == "https://notion.so/pag-nueva"
    creada = falso.creadas[0]
    props = creada["properties"]
    assert props["Código"]["title"][0]["text"]["content"] == informe.codigo
    assert props["Monto Cotizado"]["number"] == informe.monto_cotizado
    # El relato va al cuerpo, nunca a una columna.
    assert not any("exto" in clave or "elato" in clave for clave in props)
    assert creada["children"], "el relato clínico tiene que ir en el cuerpo"


def test_un_relato_enorme_se_anexa_en_tandas_de_cien():
    """Notion acepta 100 hijos por peticion; el resto va en llamadas sucesivas."""
    falso = _NotionFalso()
    largo = INFORMES[0].model_copy(
        update={"texto": "\n\n".join(f"Párrafo {i}." for i in range(250))}
    )
    asyncio.run(repositorio(falso).crear_informe(largo))

    assert len(falso.creadas[0]["children"]) == 100
    assert [len(t) for t in falso.anexados] == [100, 50]


def test_crear_poliza_no_manda_cuerpo():
    falso = _NotionFalso()
    asyncio.run(repositorio(falso).crear_poliza(POLIZAS[0]))
    assert "children" not in falso.creadas[0]


# ---------------------------------------------------------------- edicion


def test_editar_un_informe_reemplaza_el_cuerpo_entero():
    falso = _NotionFalso(filas=[fila_de("INF-2026-0031", "Código")])
    nuevo = INFORMES[0].model_copy(update={"texto": "Relato nuevo.\n\nSegundo párrafo."})

    url = asyncio.run(repositorio(falso).actualizar_informe("INF-2026-0031", nuevo))

    assert url == "https://notion.so/editada"
    assert falso.actualizadas[0]["erase_content"] is True
    # Y lo que se anexa es exactamente el relato nuevo, sin restos del viejo.
    assert falso.anexados == [parrafos(nuevo.texto)]
    assert falso.borrados == []


def test_si_notion_rechaza_erase_content_se_borra_bloque_a_bloque():
    """
    La red que permite seguir editando si ese parametro no existe en la API.
    Sin ella, un rechazo dejaria la edicion inservible.
    """
    falso = _NotionFalso(filas=[fila_de("INF-2026-0031", "Código")])
    falso.rechazar_erase = True
    nuevo = INFORMES[0].model_copy(update={"texto": "Relato nuevo."})

    asyncio.run(repositorio(falso).actualizar_informe("INF-2026-0031", nuevo))

    assert falso.borrados == ["bloque-viejo-1", "bloque-viejo-2"]
    assert falso.anexados == [parrafos(nuevo.texto)]
    assert "erase_content" not in falso.actualizadas[0]


def test_editar_algo_que_no_existe_lo_dice():
    falso = _NotionFalso(filas=[])
    with pytest.raises(RegistroNoEncontrado, match="INF-NO-EXISTE"):
        asyncio.run(repositorio(falso).actualizar_informe("INF-NO-EXISTE", INFORMES[0]))
    assert falso.actualizadas == []


def test_editar_una_poliza_no_borra_su_cuerpo():
    """Una persona puede haber escrito notas en la página; no son nuestras."""
    falso = _NotionFalso(filas=[fila_de("POL-2024-0148", "Número de Póliza")])
    asyncio.run(repositorio(falso).actualizar_poliza("POL-2024-0148", POLIZAS[0]))
    assert "erase_content" not in falso.actualizadas[0]
    assert falso.borrados == []


# ------------------------------------------------------------- identidad


def test_el_codigo_sale_del_mayor_del_ano():
    falso = _NotionFalso(filas=[fila_de(c, "Código") for c in ("INF-2026-0031", "INF-2026-0038")])
    assert asyncio.run(repositorio(falso).siguiente_codigo_informe(2026)) == "INF-2026-0039"


def test_un_hueco_en_la_numeracion_no_se_reutiliza():
    """
    Reutilizar un codigo haria que dos casos distintos compartieran folio en la
    bitacora de Postgres, que lo guarda como texto y no los distingue.
    """
    falso = _NotionFalso(filas=[fila_de(c, "Código") for c in ("INF-2026-0031", "INF-2026-0039")])
    assert asyncio.run(repositorio(falso).siguiente_codigo_informe(2026)) == "INF-2026-0040"


def test_el_primero_del_ano_empieza_en_uno():
    assert (
        asyncio.run(repositorio(_NotionFalso()).siguiente_codigo_informe(2027)) == "INF-2027-0001"
    )


# ------------------------------------------------ el arreglo del N+1


def test_comprobar_si_existe_no_descarga_la_base_entera():
    """
    Guarda contra que alguien "simplifique" esto de vuelta a listar y filtrar en
    memoria: para los informes eso descargaba ademas el relato de cada fila.
    """
    falso = _NotionFalso(filas=[fila_de("INF-2026-0031", "Código")])
    assert asyncio.run(repositorio(falso).existe_informe("INF-2026-0031")) is True

    assert len(falso.consultas) == 1
    consulta = falso.consultas[0]
    assert consulta["page_size"] == 1
    assert consulta["filter"] == {"property": "Código", "title": {"equals": "INF-2026-0031"}}


def test_obtener_una_poliza_es_una_sola_consulta_filtrada():
    fila = {"id": "p1", "properties": como_lo_devuelve_notion(propiedades_poliza(POLIZAS[0]))}
    falso = _NotionFalso(filas=[fila])

    poliza = asyncio.run(repositorio(falso).obtener_poliza("POL-2024-0148"))

    assert poliza is not None and poliza.numero == "POL-2024-0148"
    assert len(falso.consultas) == 1
    assert falso.consultas[0]["filter"]["title"]["equals"] == "POL-2024-0148"
