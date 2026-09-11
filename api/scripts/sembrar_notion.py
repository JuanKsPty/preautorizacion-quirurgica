"""
Siembra las cuatro bases de Notion con los datos de `datos_demo.py`.

    uv run --directory api python scripts/sembrar_notion.py [--rehacer]

Existe para que la carga sea reproducible y para que las dos fuentes de datos
—Notion y el respaldo local— no puedan divergir: las dos salen del mismo modulo.

Requiere en el entorno NOTION_TOKEN y los cuatro NOTION_DB_*. Por defecto es
idempotente: salta las filas cuyo identificador ya existe. Con --rehacer envia
todo de nuevo (crea duplicados; util solo sobre bases vacias).

Las bases hay que crearlas antes, con estas columnas exactas:

  Polizas                  Numero de Poliza (titulo), Titular, Cedula, Plan,
                           Estado, Inicio de Vigencia, Fin de Vigencia,
                           Deducible Anual, Deducible Consumido, Coaseguro %,
                           Tope Anual, Tope Consumido, Red Preferente,
                           Preexistencias Declaradas, Dependientes

  Informes Medicos         Codigo (titulo), Paciente, Cedula,
                           Numero de Poliza, Hospital, Medico Tratante,
                           Especialidad, Fecha del Informe,
                           Fecha Propuesta de Cirugia, Es Emergencia,
                           Monto Cotizado, Documentos Adjuntos
                           (el relato clinico va en el CUERPO de la pagina)

  Catalogo de              Codigo CPT (titulo), Nombre, Sinonimos, Categoria,
  Procedimientos           Carencia {Basico,Preferente,Ejecutivo} (dias),
                           Cobertura {Basico,Preferente,Ejecutivo} %,
                           Documentos Requeridos, Exclusion

  Pre-autorizaciones       las escribe el agente, no este script
"""

import argparse
import asyncio
import sys

from notion_client import AsyncClient

from app.core.config import settings
from app.repositorios.datos_demo import INFORMES, POLIZAS, PROCEDIMIENTOS

# Los constructores de propiedades son los MISMOS que usa la API para escribir.
# Antes este script tenia su propia copia de los nombres de columna, y dos copias
# acaban separandose sin que nadie se entere.
from app.repositorios.escritura import (
    a_multi_select,
    a_rich_text,
    parrafos,
    propiedades_informe,
    propiedades_poliza,
)


async def data_source(cliente: AsyncClient, database_id: str) -> str:
    """Desde la version 2025-09-03 las paginas se crean bajo un data source."""
    base = await cliente.databases.retrieve(database_id=database_id)
    fuentes = base.get("data_sources") or []
    if not fuentes:
        raise SystemExit(f"La base {database_id} no expone data sources.")
    return fuentes[0]["id"]


async def titulos_existentes(cliente: AsyncClient, data_source_id: str, columna: str) -> set[str]:
    existentes: set[str] = set()
    cursor: str | None = None
    while True:
        pagina = await cliente.data_sources.query(
            data_source_id=data_source_id,
            page_size=100,
            **({"start_cursor": cursor} if cursor else {}),
        )
        for fila in pagina.get("results", []):
            prop = fila.get("properties", {}).get(columna, {})
            fragmentos = prop.get("title") or []
            texto = "".join(f.get("plain_text", "") for f in fragmentos).strip()
            if texto:
                existentes.add(texto)
        if not pagina.get("has_more"):
            return existentes
        cursor = pagina.get("next_cursor")


async def sembrar(rehacer: bool) -> None:
    if not settings.notion_token.strip():
        raise SystemExit("Falta NOTION_TOKEN en el entorno.")

    faltan = [
        nombre
        for nombre, valor in (
            ("NOTION_DB_POLIZAS", settings.notion_db_polizas),
            ("NOTION_DB_INFORMES", settings.notion_db_informes),
            ("NOTION_DB_PROCEDIMIENTOS", settings.notion_db_procedimientos),
        )
        if not valor.strip()
    ]
    if faltan:
        raise SystemExit("Faltan variables: " + ", ".join(faltan))

    cliente = AsyncClient(auth=settings.notion_token, notion_version=settings.notion_version)

    ds_polizas = await data_source(cliente, settings.notion_db_polizas)
    ds_informes = await data_source(cliente, settings.notion_db_informes)
    ds_procs = await data_source(cliente, settings.notion_db_procedimientos)

    ya_polizas = (
        set() if rehacer else await titulos_existentes(cliente, ds_polizas, "Número de Póliza")
    )
    ya_informes = set() if rehacer else await titulos_existentes(cliente, ds_informes, "Código")
    ya_procs = set() if rehacer else await titulos_existentes(cliente, ds_procs, "Código CPT")

    creadas = 0
    for poliza in POLIZAS:
        if poliza.numero in ya_polizas:
            continue
        await cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": ds_polizas},
            properties=propiedades_poliza(poliza),
        )
        creadas += 1
    print(f"pólizas: {creadas} nuevas, {len(POLIZAS) - creadas} ya estaban")

    creadas = 0
    for proc in PROCEDIMIENTOS:
        if proc.cpt in ya_procs:
            continue
        await cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": ds_procs},
            properties={
                "Código CPT": {"title": a_rich_text(proc.cpt)},
                "Nombre": {"rich_text": a_rich_text(proc.nombre)},
                "Sinónimos": {"rich_text": a_rich_text(";".join(proc.sinonimos))},
                "Categoría": {"select": {"name": proc.categoria}},
                "Carencia Básico (días)": {"number": proc.carencia_dias["basico"]},
                "Carencia Preferente (días)": {"number": proc.carencia_dias["preferente"]},
                "Carencia Ejecutivo (días)": {"number": proc.carencia_dias["ejecutivo"]},
                "Cobertura Básico %": {"number": proc.cobertura_porcentaje["basico"]},
                "Cobertura Preferente %": {"number": proc.cobertura_porcentaje["preferente"]},
                "Cobertura Ejecutivo %": {"number": proc.cobertura_porcentaje["ejecutivo"]},
                "Documentos Requeridos": {
                    "multi_select": a_multi_select(proc.documentos_requeridos)
                },
                "Exclusión": {"rich_text": a_rich_text(proc.exclusion or "")},
            },
        )
        creadas += 1
    print(f"procedimientos: {creadas} nuevos, {len(PROCEDIMIENTOS) - creadas} ya estaban")

    creadas = 0
    for informe in INFORMES:
        if informe.codigo in ya_informes:
            continue
        await cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": ds_informes},
            properties=propiedades_informe(informe),
            # El relato clinico va en el cuerpo: rich_text tope a 2000 caracteres.
            children=parrafos(informe.texto),
        )
        creadas += 1
    print(f"informes: {creadas} nuevos, {len(INFORMES) - creadas} ya estaban")


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra las bases de Notion.")
    parser.add_argument(
        "--rehacer",
        action="store_true",
        help="envía todo de nuevo sin comprobar duplicados (solo sobre bases vacías)",
    )
    argumentos = parser.parse_args()
    try:
        asyncio.run(sembrar(argumentos.rehacer))
    except SystemExit as error:
        print(error, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
