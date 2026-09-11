"""
Contrato de acceso a datos.

Dos implementaciones lo cumplen: `NotionRepositorio`, que lee de las bases de
Notion, y `RepositorioDemo`, que sirve los mismos registros desde el codigo. La
fabrica elige segun haya token de Notion configurado.

Es asincrono a proposito: la evaluacion corre dentro de un generador async que
esta transmitiendo eventos SSE, y una llamada HTTP sincrona ahi bloquearia el
event loop, congelando los latidos y cualquier otro stream en curso.
"""

import asyncio
from typing import Protocol, runtime_checkable

from app.dominio.esquemas import Dictamen, InformeMedico, Poliza, Procedimiento


@runtime_checkable
class RepositorioClinico(Protocol):
    @property
    def origen(self) -> str:
        """ "notion" o "demo". Se reporta en /api/health y en cada evaluacion."""
        ...

    async def listar_polizas(self) -> list[Poliza]: ...

    async def obtener_poliza(self, numero: str) -> Poliza | None: ...

    async def listar_informes(self) -> list[InformeMedico]: ...

    async def obtener_informe(self, codigo: str) -> InformeMedico | None: ...

    async def listar_procedimientos(self) -> list[Procedimiento]: ...

    async def registrar_dictamen(self, dictamen: Dictamen) -> str | None:
        """Devuelve la URL del registro creado, o None si no se pudo escribir."""
        ...


@runtime_checkable
class RepositorioEscritura(Protocol):
    """
    Lo que sabe ESCRIBIR el expediente. Solo Notion lo cumple.

    Vive aparte de `RepositorioClinico` a proposito: la lectura tiene respaldo
    local y la escritura NO. Si fueran el mismo Protocol, `RepositorioDemo`
    tendria que fingir que escribe — y fingir que se guardo algo que no se
    guardo es el unico fallo que este sistema no puede permitirse.

    Por eso `RepositorioDemo` tampoco recibe stubs que lancen: `runtime_checkable`
    solo comprueba que el ATRIBUTO exista, asi que un stub haria que
    `isinstance(demo, RepositorioEscritura)` diera True y destruiria la unica
    comprobacion barata que hay.

    Cada mutador devuelve la URL de la pagina en Notion: es lo unico que solo
    Notion puede dar, y es lo que permite enseñar el registro recien creado.
    """

    #: Serializa generar -> comprobar -> crear. Notion no tiene restriccion de
    #: unicidad ni transacciones, asi que el candado es lo unico que cierra la
    #: carrera entre dos altas simultaneas. Es por proceso.
    candado_escritura: asyncio.Lock

    async def crear_poliza(self, poliza: Poliza) -> str: ...

    async def actualizar_poliza(self, numero: str, poliza: Poliza) -> str: ...

    async def crear_informe(self, informe: InformeMedico) -> str: ...

    async def actualizar_informe(self, codigo: str, informe: InformeMedico) -> str: ...

    async def existe_poliza(self, numero: str) -> bool: ...

    async def existe_informe(self, codigo: str) -> bool: ...

    async def siguiente_numero_poliza(self, anio: int) -> str: ...

    async def siguiente_codigo_informe(self, anio: int) -> str: ...
