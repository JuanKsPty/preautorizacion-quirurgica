"""
Lectura y escritura contra las bases de Notion.

Dos cosas que cambiaron en la API de Notion y que rompen el codigo escrito de
memoria:

  1. Desde la version 2025-09-03 `databases.query` NO EXISTE. Una base puede
     tener varias "data sources" y las consultas van a
     /v1/data_sources/{id}/query. El identificador sale de
     databases.retrieve(...)["data_sources"][0]["id"], asi que hace falta un
     paso de descubrimiento; se cachea porque no cambia.
  2. El esquema de columnas tambien se movio al data source.

Se usa `AsyncClient` y no `Client`: el cliente sincrono es httpx bloqueante y
llamarlo dentro del generador que transmite el SSE congelaria el event loop.

El texto del informe medico vive en el CUERPO de la pagina, no en una columna:
`rich_text` esta limitado a 2000 caracteres y un relato clinico se acerca
demasiado a ese techo.
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

from notion_client import AsyncClient

from app.core.config import settings
from app.dominio.esquemas import (
    NOMBRE_PLAN,
    Dictamen,
    InformeMedico,
    Poliza,
    Procedimiento,
)
from app.repositorios.escritura import (
    a_multi_select,
    a_rich_text,
    parrafos,
    propiedades_informe,
    propiedades_poliza,
)
from app.repositorios.propiedades import (
    entero,
    fecha,
    lista_separada,
    marca,
    numero,
    opcion,
    opciones,
    texto,
)

logger = logging.getLogger("app.notion")


class RegistroNoEncontrado(LookupError):
    """Se pidio editar una fila que no esta en Notion."""


# Notion acepta como mucho 100 hijos por peticion de append.
TOPE_HIJOS = 100
# Los codigos son INF-AAAA-NNNN y POL-AAAA-NNNN.
PATRON_SECUENCIA = re.compile(r"^(?:INF|POL)-(\d{4})-(\d{4})$")

# "Preferente" -> "preferente". Al leer aceptamos la etiqueta que se ve en Notion.
PLAN_DESDE_NOMBRE: dict[str, str] = {v.lower(): k for k, v in NOMBRE_PLAN.items()}


def _plan(etiqueta: str) -> str:
    return PLAN_DESDE_NOMBRE.get(etiqueta.strip().lower(), "basico")


class NotionRepositorio:
    """Lee polizas, informes y catalogo de Notion; escribe los dictamenes."""

    def __init__(self, cliente: AsyncClient | None = None) -> None:
        self._cliente = cliente or AsyncClient(
            auth=settings.notion_token,
            notion_version=settings.notion_version,
        )
        self._data_sources: dict[str, str] = {}
        self._candado = asyncio.Lock()
        # Serializa generar -> comprobar -> crear. Notion no tiene restriccion
        # de unicidad ni transacciones, asi que esto es lo unico que cierra la
        # carrera entre dos altas simultaneas. Es por proceso: con varios
        # workers la ventana se reabre.
        self.candado_escritura = asyncio.Lock()

    @property
    def origen(self) -> str:
        return "notion"

    # ------------------------------------------------------------------ infra

    async def _data_source(self, database_id: str) -> str:
        async with self._candado:
            if database_id not in self._data_sources:
                base = await self._cliente.databases.retrieve(database_id=database_id)
                fuentes = base.get("data_sources") or []
                if not fuentes:
                    raise RuntimeError(f"La base {database_id} no expone data sources")
                self._data_sources[database_id] = fuentes[0]["id"]
            return self._data_sources[database_id]

    async def _filas(self, database_id: str) -> list[dict[str, Any]]:
        """Todas las filas de una base, siguiendo la paginacion por cursor."""
        data_source_id = await self._data_source(database_id)
        filas: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            pagina = await self._cliente.data_sources.query(
                data_source_id=data_source_id,
                page_size=100,
                **({"start_cursor": cursor} if cursor else {}),
            )
            filas.extend(pagina.get("results", []))
            if not pagina.get("has_more"):
                return filas
            cursor = pagina.get("next_cursor")

    async def _cuerpo(self, page_id: str) -> str:
        """Concatena los parrafos de la pagina: ahi va el relato clinico."""
        partes: list[str] = []
        cursor: str | None = None
        while True:
            respuesta = await self._cliente.blocks.children.list(
                block_id=page_id,
                page_size=100,
                **({"start_cursor": cursor} if cursor else {}),
            )
            for bloque in respuesta.get("results", []):
                if bloque.get("type") != "paragraph":
                    continue
                fragmentos = bloque.get("paragraph", {}).get("rich_text", [])
                linea = "".join(f.get("plain_text", "") for f in fragmentos if isinstance(f, dict))
                if linea.strip():
                    partes.append(linea.strip())
            if not respuesta.get("has_more"):
                return "\n\n".join(partes)
            cursor = respuesta.get("next_cursor")

    # ----------------------------------------------------------------- lectura

    async def listar_polizas(self) -> list[Poliza]:
        filas = await self._filas(settings.notion_db_polizas)
        return [p for p in (self._a_poliza(f) for f in filas) if p is not None]

    async def obtener_poliza(self, numero_poliza: str) -> Poliza | None:
        """Consulta filtrada en el servidor: una fila, no toda la base."""
        fila = await self._buscar_pagina(
            settings.notion_db_polizas, "Número de Póliza", numero_poliza.strip()
        )
        return self._a_poliza(fila) if fila else None

    async def listar_informes(self) -> list[InformeMedico]:
        filas = await self._filas(settings.notion_db_informes)
        informes = await asyncio.gather(
            *(self._a_informe(f) for f in filas), return_exceptions=True
        )
        resultado: list[InformeMedico] = []
        for informe in informes:
            if isinstance(informe, InformeMedico):
                resultado.append(informe)
            elif isinstance(informe, Exception):
                logger.warning("Informe ilegible en Notion: %s", informe)
        return resultado

    async def obtener_informe(self, codigo: str) -> InformeMedico | None:
        """
        Una consulta filtrada mas el cuerpo de esa fila: dos llamadas.

        Antes listaba la base entera y filtraba en memoria. Como `listar_informes`
        pide el relato clinico de CADA fila, evaluar un solo caso descargaba el
        relato de todos: 9 viajes con los 8 sembrados, creciendo con cada alta,
        contra un limite de ~3 peticiones por segundo. Y un 429 dispara la
        degradacion de 60 segundos, que hace desaparecer lo recien creado.
        """
        fila = await self._buscar_pagina(settings.notion_db_informes, "Código", codigo.strip())
        return await self._a_informe(fila) if fila else None

    async def listar_procedimientos(self) -> list[Procedimiento]:
        filas = await self._filas(settings.notion_db_procedimientos)
        return [p for p in (self._a_procedimiento(f) for f in filas) if p is not None]

    # -------------------------------------------------------------- conversion

    def _a_poliza(self, fila: dict[str, Any]) -> Poliza | None:
        props = fila.get("properties", {})
        numero_poliza = texto(props, "Número de Póliza")
        inicio = fecha(props, "Inicio de Vigencia")
        fin = fecha(props, "Fin de Vigencia")
        if not numero_poliza or inicio is None or fin is None:
            logger.warning("Fila de póliza incompleta en Notion: %s", fila.get("id"))
            return None
        return Poliza(
            numero=numero_poliza,
            titular=texto(props, "Titular"),
            cedula=texto(props, "Cédula"),
            plan=_plan(opcion(props, "Plan", "Básico")),  # type: ignore[arg-type]
            estado=opcion(props, "Estado", "vigente"),  # type: ignore[arg-type]
            inicio_vigencia=inicio,
            fin_vigencia=fin,
            deducible_anual=numero(props, "Deducible Anual"),
            deducible_consumido=numero(props, "Deducible Consumido"),
            coaseguro_porcentaje=entero(props, "Coaseguro %"),
            tope_anual=numero(props, "Tope Anual"),
            tope_consumido=numero(props, "Tope Consumido"),
            red_preferente=marca(props, "Red Preferente", True),
            preexistencias_declaradas=opciones(props, "Preexistencias Declaradas"),
            dependientes=lista_separada(props, "Dependientes", ";"),
        )

    async def _a_informe(self, fila: dict[str, Any]) -> InformeMedico | None:
        props = fila.get("properties", {})
        codigo = texto(props, "Código")
        fecha_informe = fecha(props, "Fecha del Informe")
        fecha_cirugia = fecha(props, "Fecha Propuesta de Cirugía")
        if not codigo or fecha_informe is None or fecha_cirugia is None:
            logger.warning("Fila de informe incompleta en Notion: %s", fila.get("id"))
            return None
        return InformeMedico(
            codigo=codigo,
            paciente=texto(props, "Paciente"),
            cedula=texto(props, "Cédula"),
            numero_poliza=texto(props, "Número de Póliza"),
            hospital=opcion(props, "Hospital"),
            medico_tratante=texto(props, "Médico Tratante"),
            especialidad=opcion(props, "Especialidad"),
            fecha_informe=fecha_informe,
            fecha_cirugia_propuesta=fecha_cirugia,
            es_emergencia=marca(props, "Es Emergencia"),
            monto_cotizado=numero(props, "Monto Cotizado"),
            documentos_adjuntos=opciones(props, "Documentos Adjuntos"),
            texto=await self._cuerpo(fila["id"]),
        )

    def _a_procedimiento(self, fila: dict[str, Any]) -> Procedimiento | None:
        props = fila.get("properties", {})
        cpt = texto(props, "Código CPT")
        if not cpt:
            return None
        # Notion no tiene tipo mapa: una columna por nivel de plan.
        return Procedimiento(
            cpt=cpt,
            nombre=texto(props, "Nombre"),
            sinonimos=lista_separada(props, "Sinónimos", ";"),
            categoria=opcion(props, "Categoría"),
            carencia_dias={
                "basico": entero(props, "Carencia Básico (días)"),
                "preferente": entero(props, "Carencia Preferente (días)"),
                "ejecutivo": entero(props, "Carencia Ejecutivo (días)"),
            },
            cobertura_porcentaje={
                "basico": entero(props, "Cobertura Básico %"),
                "preferente": entero(props, "Cobertura Preferente %"),
                "ejecutivo": entero(props, "Cobertura Ejecutivo %"),
            },
            documentos_requeridos=opciones(props, "Documentos Requeridos"),
            exclusion=texto(props, "Exclusión") or None,
        )

    # --------------------------------------------------------------- escritura

    async def registrar_dictamen(self, dictamen: Dictamen) -> str | None:
        """
        Escribe el dictamen en la base de Pre-autorizaciones.

        Es best-effort: el veredicto ya se transmitio al navegador y ya quedo en
        Postgres, asi que un fallo aqui se registra y no se propaga.
        """
        if not settings.notion_db_preautorizaciones.strip():
            return None

        desglose = dictamen.desglose
        propiedades: dict[str, Any] = {
            "Folio": {"title": a_rich_text(dictamen.folio)},
            "Veredicto": {"select": {"name": dictamen.veredicto}},
            "Póliza": {"rich_text": a_rich_text(dictamen.numero_poliza)},
            "Informe": {"rich_text": a_rich_text(dictamen.codigo_informe)},
            "Paciente": {"rich_text": a_rich_text(dictamen.paciente)},
            "CPT": {"rich_text": a_rich_text(dictamen.cpt_identificado or "")},
            "Procedimiento": {"rich_text": a_rich_text(dictamen.procedimiento_identificado or "")},
            "CIE-10": {"rich_text": a_rich_text(dictamen.cie10_identificado or "")},
            # `opciones` quita las comas: Notion devuelve 400 si una opcion
            # lleva una, y un nombre de documento puede traerla.
            "Documentos Faltantes": {"multi_select": a_multi_select(dictamen.documentos_faltantes)},
            "Evaluado en": {"date": {"start": datetime.now(UTC).isoformat()}},
        }
        if desglose is not None:
            propiedades |= {
                "Monto Cotizado": {"number": desglose.monto_cotizado},
                "Cubre Aseguradora": {"number": desglose.cubierto_aseguradora},
                "A Cargo del Paciente": {"number": desglose.a_cargo_paciente},
            }

        hijos: list[dict[str, Any]] = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": a_rich_text("Resolución para el paciente")},
            },
            *parrafos(dictamen.carta_paciente),
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": a_rich_text("Justificación técnica")},
            },
            *parrafos(dictamen.justificacion_tecnica),
        ]

        data_source_id = await self._data_source(settings.notion_db_preautorizaciones)
        pagina = await self._cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=propiedades,
            children=hijos,
        )
        return pagina.get("url")

    # ------------------------------------------------------------ busqueda

    async def _filas_filtradas(
        self, database_id: str, filtro: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Como `_filas`, pero deja el filtrado en el servidor de Notion."""
        data_source_id = await self._data_source(database_id)
        filas: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            pagina = await self._cliente.data_sources.query(
                data_source_id=data_source_id,
                filter=filtro,
                page_size=100,
                **({"start_cursor": cursor} if cursor else {}),
            )
            filas.extend(pagina.get("results", []))
            if not pagina.get("has_more"):
                return filas
            cursor = pagina.get("next_cursor")

    async def _buscar_pagina(
        self, database_id: str, columna: str, valor: str
    ) -> dict[str, Any] | None:
        """
        Una fila por el valor exacto de su columna titulo, en UNA peticion.

        Es lo que evita el patron "lista toda la base y filtra en memoria": para
        los informes eso ademas descargaba el relato clinico de cada fila, asi
        que responder a un si/no costaba 1+N viajes y crecia con cada alta.
        """
        data_source_id = await self._data_source(database_id)
        pagina = await self._cliente.data_sources.query(
            data_source_id=data_source_id,
            filter={"property": columna, "title": {"equals": valor}},
            page_size=1,
        )
        resultados = pagina.get("results", [])
        return resultados[0] if resultados else None

    async def existe_informe(self, codigo: str) -> bool:
        return (
            await self._buscar_pagina(settings.notion_db_informes, "Código", codigo)
        ) is not None

    async def existe_poliza(self, numero: str) -> bool:
        return (
            await self._buscar_pagina(settings.notion_db_polizas, "Número de Póliza", numero)
        ) is not None

    # -------------------------------------------------- generacion de codigos

    async def _siguiente(self, database_id: str, columna: str, prefijo: str, anio: int) -> str:
        """
        `max + 1` sobre lo que hay en Notion, sin reutilizar huecos.

        Si existen 0031 y 0039, el siguiente es 0040 y no 0032: un codigo
        reutilizado apuntaria a dos casos distintos en la bitacora de Postgres,
        que guarda el codigo como texto y no distingue.

        Se cuenta sobre Notion y no sobre una tabla propia a proposito: alguien
        puede añadir una fila a mano —el seeder lo pone facil— y una secuencia
        en Postgres se desincronizaria en silencio.
        """
        filas = await self._filas_filtradas(
            database_id,
            {"property": columna, "title": {"starts_with": f"{prefijo}-{anio}-"}},
        )
        mayor = 0
        for fila in filas:
            encontrado = PATRON_SECUENCIA.match(texto(fila.get("properties", {}), columna))
            if encontrado and int(encontrado.group(1)) == anio:
                mayor = max(mayor, int(encontrado.group(2)))
        return f"{prefijo}-{anio}-{mayor + 1:04d}"

    async def siguiente_codigo_informe(self, anio: int) -> str:
        return await self._siguiente(settings.notion_db_informes, "Código", "INF", anio)

    async def siguiente_numero_poliza(self, anio: int) -> str:
        return await self._siguiente(settings.notion_db_polizas, "Número de Póliza", "POL", anio)

    # ---------------------------------------------------------- cuerpo de pagina

    async def _anexar(self, page_id: str, bloques: list[dict[str, Any]]) -> None:
        """`blocks.children.append` acepta 100 hijos por peticion."""
        for inicio in range(0, len(bloques), TOPE_HIJOS):
            await self._cliente.blocks.children.append(
                block_id=page_id, children=bloques[inicio : inicio + TOPE_HIJOS]
            )

    async def _vaciar_cuerpo(self, page_id: str) -> None:
        """
        Respaldo: borra los bloques uno a uno.

        Solo se usa si la API rechaza `erase_content`. Es peor camino —los
        borrados son secuenciales y un 429 a mitad deja la pagina con el relato
        truncado— pero es preferible a no poder editar.
        """
        identificadores: list[str] = []
        cursor: str | None = None
        while True:
            respuesta = await self._cliente.blocks.children.list(
                block_id=page_id,
                page_size=100,
                **({"start_cursor": cursor} if cursor else {}),
            )
            identificadores.extend(b["id"] for b in respuesta.get("results", []))
            if not respuesta.get("has_more"):
                break
            cursor = respuesta.get("next_cursor")
        for identificador in identificadores:
            await self._cliente.blocks.delete(block_id=identificador)

    # ---------------------------------------------------------------- alta

    async def crear_poliza(self, poliza: Poliza) -> str:
        data_source_id = await self._data_source(settings.notion_db_polizas)
        pagina = await self._cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=propiedades_poliza(poliza),
        )
        return pagina.get("url", "")

    async def crear_informe(self, informe: InformeMedico) -> str:
        data_source_id = await self._data_source(settings.notion_db_informes)
        bloques = parrafos(informe.texto)
        pagina = await self._cliente.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=propiedades_informe(informe),
            children=bloques[:TOPE_HIJOS],
        )
        await self._anexar(pagina["id"], bloques[TOPE_HIJOS:])
        return pagina.get("url", "")

    # --------------------------------------------------------------- edicion

    async def actualizar_poliza(self, numero: str, poliza: Poliza) -> str:
        pagina = await self._buscar_pagina(settings.notion_db_polizas, "Número de Póliza", numero)
        if pagina is None:
            raise RegistroNoEncontrado(f"No existe la póliza {numero}")
        # Sin `erase_content`: una poliza no tiene cuerpo en nuestro modelo, pero
        # una persona puede haber escrito notas en la pagina. Borrarlas seria una
        # eliminacion que nadie pidio.
        actualizada = await self._cliente.pages.update(
            page_id=pagina["id"], properties=propiedades_poliza(poliza)
        )
        return actualizada.get("url", "")

    async def actualizar_informe(self, codigo: str, informe: InformeMedico) -> str:
        """
        Reemplaza propiedades y relato.

        `erase_content=True` vacia el cuerpo en el servidor, de forma atomica, y
        deja el trabajo en dos peticiones en vez de una por bloque. Si la API lo
        rechaza se cae al borrado bloque a bloque: el parametro esta en la lista
        del SDK pero no se ha podido confirmar contra Notion en vivo, y quedarse
        sin poder editar seria peor que hacerlo por el camino lento.
        """
        pagina = await self._buscar_pagina(settings.notion_db_informes, "Código", codigo)
        if pagina is None:
            raise RegistroNoEncontrado(f"No existe el informe {codigo}")

        propiedades = propiedades_informe(informe)
        try:
            actualizada = await self._cliente.pages.update(
                page_id=pagina["id"], properties=propiedades, erase_content=True
            )
        except Exception as error:
            logger.warning(
                "Notion no aceptó erase_content (%s); se vacía el cuerpo bloque a bloque.",
                error,
            )
            actualizada = await self._cliente.pages.update(
                page_id=pagina["id"], properties=propiedades
            )
            await self._vaciar_cuerpo(pagina["id"])

        await self._anexar(pagina["id"], parrafos(informe.texto))
        return actualizada.get("url", "")
