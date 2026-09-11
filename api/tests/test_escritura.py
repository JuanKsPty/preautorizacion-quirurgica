"""
Los constructores de propiedades de Notion.

La prueba que de verdad importa es la de ida y vuelta: escribir una poliza y
volver a leerla tiene que devolver exactamente la misma poliza. Eso caza un
renombrado de columna hecho en un solo sentido, que es el fallo que este modulo
existe para evitar — antes los nombres estaban en dos sitios y podian separarse.
"""

import asyncio

from app.repositorios.datos_demo import INFORMES, POLIZAS
from app.repositorios.escritura import (
    TOPE_BLOQUE,
    TOPE_TEXTO,
    a_multi_select,
    a_rich_text,
    a_select,
    parrafos,
    propiedades_informe,
    propiedades_poliza,
)
from app.repositorios.notion import NotionRepositorio


def repositorio_sin_red() -> NotionRepositorio:
    """Los conversores no tocan la red; basta con no dejar que construya cliente."""
    return NotionRepositorio(cliente=object())  # type: ignore[arg-type]


def como_lo_devuelve_notion(propiedades: dict) -> dict:
    """
    Aplica la UNICA asimetria entre escribir y leer en la API de Notion.

    Al escribir un `title` o un `rich_text` se manda `{"text": {"content": ...}}`.
    Al leerlos, Notion devuelve ADEMAS `plain_text` con el texto ya renderizado,
    y es ese campo el que usan los extractores de `propiedades.py`.

    Sin modelar esto, una prueba de ida y vuelta compararia la forma de escritura
    contra el parser de lectura y fallaria por una diferencia que no es un fallo
    nuestro. El resto de tipos (select, number, date, checkbox, multi_select) son
    simetricos y pasan tal cual.
    """
    devuelto = {}
    for nombre, valor in propiedades.items():
        clave = "title" if "title" in valor else ("rich_text" if "rich_text" in valor else None)
        if clave is None:
            devuelto[nombre] = valor
            continue
        devuelto[nombre] = {
            clave: [{**f, "plain_text": f["text"]["content"]} for f in valor[clave]]
        }
    return devuelto


# ------------------------------------------------------------------ helpers


def test_un_select_vacio_se_manda_como_null():
    """`{"select": {"name": ""}}` devuelve 400; Notion quiere null."""
    assert a_select("") is None
    assert a_select("   ") is None
    assert a_select("Cirugía general") == {"name": "Cirugía general"}


def test_una_coma_no_llega_a_notion():
    """
    Notion RECHAZA la coma dentro del nombre de una opcion: devuelve 400, no la
    escapa. Un nombre de documento con coma no puede tumbar el guardado.
    """
    assert a_multi_select(["Informe médico, firmado"]) == [{"name": "Informe médico  firmado"}]


def test_las_opciones_vacias_se_descartan():
    assert a_multi_select(["Copia de cédula", "", "   "]) == [{"name": "Copia de cédula"}]


def test_un_nombre_de_opcion_larguisimo_se_trunca():
    assert len(a_multi_select(["x" * 500])[0]["name"]) == 100


def test_un_texto_largo_se_trocea_bajo_el_limite_de_notion():
    fragmentos = a_rich_text("y" * 5000)
    assert len(fragmentos) == 3
    assert all(len(f["text"]["content"]) <= TOPE_TEXTO for f in fragmentos)
    assert "".join(f["text"]["content"] for f in fragmentos) == "y" * 5000


def test_un_texto_vacio_no_produce_fragmentos():
    assert a_rich_text("") == []


def test_los_parrafos_respetan_el_salto_doble():
    bloques = parrafos("Primero.\n\nSegundo.\n\n\n\nTercero.")
    assert len(bloques) == 3
    assert all(b["type"] == "paragraph" for b in bloques)
    assert bloques[1]["paragraph"]["rich_text"][0]["text"]["content"] == "Segundo."


def test_un_parrafo_enorme_se_parte_en_varios_bloques():
    bloques = parrafos("z" * 4000)
    assert len(bloques) == 3
    assert all(
        len(b["paragraph"]["rich_text"][0]["text"]["content"]) <= TOPE_BLOQUE for b in bloques
    )


# ---------------------------------------------------------------- la poliza


def test_la_poliza_escribe_el_plan_visible_y_el_estado_crudo():
    """
    La asimetria no es un descuido: `_a_poliza` revierte NOMBRE_PLAN para el
    plan, pero pasa el estado TAL CUAL al Literal EstadoPoliza. Escribir
    "En mora" haria estallar la lectura de todas las polizas.
    """
    props = propiedades_poliza(POLIZAS[4])  # Ernesto, en mora
    assert props["Plan"]["select"] == {"name": "Básico"}
    assert props["Estado"]["select"] == {"name": "en_mora"}


def test_la_poliza_ida_y_vuelta_es_la_misma_poliza():
    repositorio = repositorio_sin_red()
    for original in POLIZAS:
        fila = {"id": "x", "properties": como_lo_devuelve_notion(propiedades_poliza(original))}
        recuperada = repositorio._a_poliza(fila)
        assert recuperada == original, f"{original.numero} no sobrevivio el viaje"


# --------------------------------------------------------------- el informe


def test_el_relato_clinico_no_va_en_una_columna():
    """rich_text tope a 2000 caracteres: el relato va al cuerpo de la pagina."""
    props = propiedades_informe(INFORMES[0])
    assert "texto" not in props
    assert not any("elato" in clave for clave in props)


def test_el_informe_ida_y_vuelta_es_el_mismo_informe():
    """
    Incluye el cuerpo: se finge el cliente para que devuelva los parrafos que
    `propiedades_informe` dejo fuera, que es exactamente lo que hace Notion.
    """

    class _Hijos:
        def __init__(self, bloques):
            self._bloques = bloques

        async def list(self, **_):
            return {
                "results": [
                    {
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"plain_text": b["paragraph"]["rich_text"][0]["text"]["content"]}
                            ]
                        },
                    }
                    for b in self._bloques
                ],
                "has_more": False,
            }

    for original in INFORMES:
        cuerpo = parrafos(original.texto)

        class _Cliente:
            class blocks:  # noqa: N801  (imita la forma del SDK)
                children = _Hijos(cuerpo)

        repositorio = NotionRepositorio(cliente=_Cliente())  # type: ignore[arg-type]
        fila = {"id": "x", "properties": como_lo_devuelve_notion(propiedades_informe(original))}
        recuperado = asyncio.run(repositorio._a_informe(fila))
        assert recuperado is not None
        # El cuerpo se reconstruye uniendo parrafos: identico al original.
        assert recuperado.texto == original.texto, f"{original.codigo}: relato alterado"
        assert recuperado.model_dump(exclude={"texto"}) == original.model_dump(exclude={"texto"}), (
            f"{original.codigo}: metadatos alterados"
        )
