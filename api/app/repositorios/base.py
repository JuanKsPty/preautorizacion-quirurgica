"""
Contrato de acceso a datos.

Dos implementaciones lo cumplen: `NotionRepositorio`, que lee de las bases de
Notion, y `RepositorioDemo`, que sirve los mismos registros desde el codigo. La
fabrica elige segun haya token de Notion configurado.

Es asincrono a proposito: la evaluacion corre dentro de un generador async que
esta transmitiendo eventos SSE, y una llamada HTTP sincrona ahi bloquearia el
event loop, congelando los latidos y cualquier otro stream en curso.
"""

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
