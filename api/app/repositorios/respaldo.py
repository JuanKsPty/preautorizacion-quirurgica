"""
Notion con red debajo.

La fabrica elige Notion cuando hay token configurado, pero un token valido no
garantiza acceso: la integracion puede no estar conectada a las paginas, Notion
puede estar caido, o puede devolver un limite de peticiones. En cualquiera de
esos casos la aplicacion tiene que seguir resolviendo con los datos locales, que
son identicos — no devolver un 500.

Este decorador es lo que convierte "hay respaldo" en algo cierto tambien en
tiempo de ejecucion, y no solo en el arranque. Recuerda el ultimo fallo para que
/api/health pueda decir por que esta degradado, en vez de dejarlo en misterio.
"""

import logging
from typing import Any

from app.dominio.esquemas import Dictamen, InformeMedico, Poliza, Procedimiento
from app.repositorios.base import RepositorioClinico

logger = logging.getLogger("app.repositorios")


class RepositorioConRespaldo:
    """Intenta el primario; ante cualquier fallo de lectura, usa el respaldo."""

    def __init__(self, primario: RepositorioClinico, respaldo: RepositorioClinico) -> None:
        self._primario = primario
        self._respaldo = respaldo
        self._degradado = False
        self.ultimo_error: str | None = None

    @property
    def origen(self) -> str:
        """El origen REAL de los datos, no el configurado."""
        return self._respaldo.origen if self._degradado else self._primario.origen

    @property
    def degradado(self) -> bool:
        return self._degradado

    async def _intentar(self, metodo: str, *args: Any) -> Any:
        if not self._degradado:
            try:
                resultado = await getattr(self._primario, metodo)(*args)
                # Una lectura correcta rehabilita el primario: si Notion vuelve,
                # se vuelve a leer de Notion sin reiniciar nada.
                self.ultimo_error = None
                return resultado
            except Exception as error:
                self._degradado = True
                self.ultimo_error = str(error).split("\n")[0][:300]
                logger.warning(
                    "Notion falló en %s; se usan los datos locales. Motivo: %s",
                    metodo,
                    self.ultimo_error,
                )
        return await getattr(self._respaldo, metodo)(*args)

    def reintentar_primario(self) -> None:
        """Vuelve a probar Notion en la siguiente lectura."""
        self._degradado = False
        self.ultimo_error = None

    async def listar_polizas(self) -> list[Poliza]:
        return await self._intentar("listar_polizas")

    async def obtener_poliza(self, numero: str) -> Poliza | None:
        return await self._intentar("obtener_poliza", numero)

    async def listar_informes(self) -> list[InformeMedico]:
        return await self._intentar("listar_informes")

    async def obtener_informe(self, codigo: str) -> InformeMedico | None:
        return await self._intentar("obtener_informe", codigo)

    async def listar_procedimientos(self) -> list[Procedimiento]:
        return await self._intentar("listar_procedimientos")

    async def registrar_dictamen(self, dictamen: Dictamen) -> str | None:
        """
        La escritura es best-effort y NO degrada la lectura: que no se pueda
        escribir el dictamen en Notion no dice nada sobre si se puede leer.
        """
        if self._degradado:
            return None
        try:
            return await self._primario.registrar_dictamen(dictamen)
        except Exception:
            logger.exception("No se pudo escribir el dictamen en Notion")
            return None
