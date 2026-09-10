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
from typing import Any

from notion_client import AsyncClient

from app.core.config import settings
from app.dominio.esquemas import NOMBRE_PLAN
from app.repositorios.datos_demo import INFORMES, POLIZAS, PROCEDIMIENTOS

TOPE_BLOQUE = 1900


def rich(contenido: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": contenido}}]


def parrafos(texto: str) -> list[dict[str, Any]]:
    bloques: list[dict[str, Any]] = []
    for parrafo in texto.split("\n\n"):
        limpio = parrafo.strip()
        if not limpio:
            continue
        for inicio in range(0, len(limpio), TOPE_BLOQUE):
            bloques.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": rich(limpio[inicio : inicio + TOPE_BLOQUE])},
                }
            )
    return bloques


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
            properties={
                "Número de Póliza": {"title": rich(poliza.numero)},
                "Titular": {"rich_text": rich(poliza.titular)},
                "Cédula": {"rich_text": rich(poliza.cedula)},
                "Plan": {"select": {"name": NOMBRE_PLAN[poliza.plan]}},
                "Estado": {"select": {"name": poliza.estado}},
                "Inicio de Vigencia": {"date": {"start": poliza.inicio_vigencia.isoformat()}},
                "Fin de Vigencia": {"date": {"start": poliza.fin_vigencia.isoformat()}},
                "Deducible Anual": {"number": poliza.deducible_anual},
                "Deducible Consumido": {"number": poliza.deducible_consumido},
                "Coaseguro %": {"number": poliza.coaseguro_porcentaje},
                "Tope Anual": {"number": poliza.tope_anual},
                "Tope Consumido": {"number": poliza.tope_consumido},
                "Red Preferente": {"checkbox": poliza.red_preferente},
                "Preexistencias Declaradas": {
                    "multi_select": [{"name": p} for p in poliza.preexistencias_declaradas]
                },
                "Dependientes": {"rich_text": rich("; ".join(poliza.dependientes))},
            },
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
                "Código CPT": {"title": rich(proc.cpt)},
                "Nombre": {"rich_text": rich(proc.nombre)},
                "Sinónimos": {"rich_text": rich(";".join(proc.sinonimos))},
                "Categoría": {"select": {"name": proc.categoria}},
                "Carencia Básico (días)": {"number": proc.carencia_dias["basico"]},
                "Carencia Preferente (días)": {"number": proc.carencia_dias["preferente"]},
                "Carencia Ejecutivo (días)": {"number": proc.carencia_dias["ejecutivo"]},
                "Cobertura Básico %": {"number": proc.cobertura_porcentaje["basico"]},
                "Cobertura Preferente %": {"number": proc.cobertura_porcentaje["preferente"]},
                "Cobertura Ejecutivo %": {"number": proc.cobertura_porcentaje["ejecutivo"]},
                "Documentos Requeridos": {
                    "multi_select": [{"name": d} for d in proc.documentos_requeridos]
                },
                "Exclusión": {"rich_text": rich(proc.exclusion or "")},
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
            properties={
                "Código": {"title": rich(informe.codigo)},
                "Paciente": {"rich_text": rich(informe.paciente)},
                "Cédula": {"rich_text": rich(informe.cedula)},
                "Número de Póliza": {"rich_text": rich(informe.numero_poliza)},
                "Hospital": {"select": {"name": informe.hospital}},
                "Médico Tratante": {"rich_text": rich(informe.medico_tratante)},
                "Especialidad": {"select": {"name": informe.especialidad}},
                "Fecha del Informe": {"date": {"start": informe.fecha_informe.isoformat()}},
                "Fecha Propuesta de Cirugía": {
                    "date": {"start": informe.fecha_cirugia_propuesta.isoformat()}
                },
                "Es Emergencia": {"checkbox": informe.es_emergencia},
                "Monto Cotizado": {"number": informe.monto_cotizado},
                "Documentos Adjuntos": {
                    "multi_select": [{"name": d} for d in informe.documentos_adjuntos]
                },
            },
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
