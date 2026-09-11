"""
Constructores de propiedades para escribir en Notion.

Son el espejo exacto de los lectores `_a_poliza` y `_a_informe` de `notion.py`.
Viven aparte porque hasta ahora los nombres de columna estaban en DOS sitios —los
lectores y `scripts/sembrar_notion.py`— y añadir un tercero garantizaba que se
separaran. Este modulo es la unica fuente: el seeder lo importa.

Todo aqui es puro: ni red, ni cliente, ni configuracion. Se prueba sin mocks.

Los nombres llevan el prefijo `a_` (a_select, a_multi_select) porque
`propiedades.py` tiene funciones homonimas que hacen lo CONTRARIO: leen esas
mismas formas. Sin el prefijo, importar las dos en el mismo modulo es un
choque de nombres — y peor, uno silencioso si alguien reordena los imports.
"""

from typing import Any

from app.dominio.esquemas import NOMBRE_PLAN, InformeMedico, Poliza

# Un fragmento de rich_text tope a 2000 caracteres. Se trocea con margen.
TOPE_TEXTO = 1900
# Un bloque de parrafo tiene el mismo limite.
TOPE_BLOQUE = 1900
# Notion rechaza un nombre de opcion mas largo que esto.
TOPE_OPCION = 100


def a_rich_text(contenido: str) -> list[dict[str, Any]]:
    """
    Trocea un texto en fragmentos de rich_text.

    `Dependientes` se guarda como una cadena unida por «;» y puede pasarse del
    limite con seis nombres largos; el troceo lo cubre sin pensarlo.
    """
    limpio = contenido or ""
    if not limpio:
        return []
    return [
        {"type": "text", "text": {"content": limpio[i : i + TOPE_TEXTO]}}
        for i in range(0, len(limpio), TOPE_TEXTO)
    ]


def a_select(valor: str) -> dict[str, str] | None:
    """
    Una opcion de `select`, o None si esta vacia.

    `{"select": {"name": ""}}` devuelve 400. Un select sin valor se manda como
    null, que es lo que Notion entiende por «sin elegir».
    """
    limpio = (valor or "").strip()
    return {"name": limpio[:TOPE_OPCION]} if limpio else None


def a_multi_select(valores: list[str]) -> list[dict[str, str]]:
    """
    Opciones de `multi_select`.

    Notion RECHAZA la coma dentro del nombre de una opcion: devuelve 400, no la
    escapa. Se sustituye por un espacio en vez de fallar, porque una coma en un
    nombre de documento no deberia tumbar el guardado de un expediente entero.
    """
    return [
        {"name": v.strip().replace(",", " ")[:TOPE_OPCION]}
        for v in (valores or [])
        if v and v.strip()
    ]


def parrafos(texto: str) -> list[dict[str, Any]]:
    """El relato clinico como bloques de parrafo, respetando los saltos dobles."""
    bloques: list[dict[str, Any]] = []
    for parrafo in (texto or "").split("\n\n"):
        limpio = parrafo.strip()
        if not limpio:
            continue
        for inicio in range(0, len(limpio), TOPE_BLOQUE):
            bloques.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": limpio[inicio : inicio + TOPE_BLOQUE]},
                            }
                        ]
                    },
                }
            )
    return bloques


def propiedades_poliza(poliza: Poliza) -> dict[str, Any]:
    """
    Espejo de `_a_poliza`. Dos asimetrias que NO son un descuido:

      * `Plan` se escribe con el nombre visible ("Preferente") porque el lector
        hace `_plan(opcion(...))`, que revierte NOMBRE_PLAN.
      * `Estado` se escribe con el literal crudo ("en_mora") porque el lector lo
        pasa TAL CUAL al Literal EstadoPoliza, sin reverso ni defecto. Escribir
        "En mora" aqui haria estallar la lectura de TODAS las polizas.
    """
    return {
        "Número de Póliza": {"title": a_rich_text(poliza.numero)},
        "Titular": {"rich_text": a_rich_text(poliza.titular)},
        "Cédula": {"rich_text": a_rich_text(poliza.cedula)},
        "Plan": {"select": a_select(NOMBRE_PLAN[poliza.plan])},
        "Estado": {"select": a_select(poliza.estado)},
        "Inicio de Vigencia": {"date": {"start": poliza.inicio_vigencia.isoformat()}},
        "Fin de Vigencia": {"date": {"start": poliza.fin_vigencia.isoformat()}},
        "Deducible Anual": {"number": poliza.deducible_anual},
        "Deducible Consumido": {"number": poliza.deducible_consumido},
        "Coaseguro %": {"number": poliza.coaseguro_porcentaje},
        "Tope Anual": {"number": poliza.tope_anual},
        "Tope Consumido": {"number": poliza.tope_consumido},
        "Red Preferente": {"checkbox": poliza.red_preferente},
        "Preexistencias Declaradas": {
            "multi_select": a_multi_select(poliza.preexistencias_declaradas)
        },
        "Dependientes": {"rich_text": a_rich_text("; ".join(poliza.dependientes))},
    }


def propiedades_informe(informe: InformeMedico) -> dict[str, Any]:
    """
    Espejo de `_a_informe`. `texto` NO esta aqui a proposito: el relato clinico
    va al CUERPO de la pagina, porque rich_text tope a 2000 caracteres y un
    informe medico se acerca demasiado.
    """
    return {
        "Código": {"title": a_rich_text(informe.codigo)},
        "Paciente": {"rich_text": a_rich_text(informe.paciente)},
        "Cédula": {"rich_text": a_rich_text(informe.cedula)},
        # rich_text y no relation: el lector hace texto(props, "Número de Póliza").
        "Número de Póliza": {"rich_text": a_rich_text(informe.numero_poliza)},
        "Hospital": {"select": a_select(informe.hospital)},
        "Médico Tratante": {"rich_text": a_rich_text(informe.medico_tratante)},
        "Especialidad": {"select": a_select(informe.especialidad)},
        "Fecha del Informe": {"date": {"start": informe.fecha_informe.isoformat()}},
        "Fecha Propuesta de Cirugía": {
            "date": {"start": informe.fecha_cirugia_propuesta.isoformat()}
        },
        "Es Emergencia": {"checkbox": informe.es_emergencia},
        "Monto Cotizado": {"number": informe.monto_cotizado},
        "Documentos Adjuntos": {"multi_select": a_multi_select(informe.documentos_adjuntos)},
    }
