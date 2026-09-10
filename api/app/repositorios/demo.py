"""
Repositorio de demostracion: los mismos registros que Notion, servidos desde
el codigo.

Existe para que el enlace publico funcione aunque Notion este caido o el token
no este configurado. Las escrituras no van a ningun sitio: la bitacora real
vive en Postgres.
"""

from app.dominio.esquemas import Dictamen, InformeMedico, Poliza, Procedimiento
from app.repositorios.datos_demo import INFORMES, POLIZAS, PROCEDIMIENTOS


class RepositorioDemo:
    @property
    def origen(self) -> str:
        return "demo"

    async def listar_polizas(self) -> list[Poliza]:
        return list(POLIZAS)

    async def obtener_poliza(self, numero: str) -> Poliza | None:
        clave = numero.strip().upper()
        return next((p for p in POLIZAS if p.numero.upper() == clave), None)

    async def listar_informes(self) -> list[InformeMedico]:
        return list(INFORMES)

    async def obtener_informe(self, codigo: str) -> InformeMedico | None:
        clave = codigo.strip().upper()
        return next((i for i in INFORMES if i.codigo.upper() == clave), None)

    async def listar_procedimientos(self) -> list[Procedimiento]:
        return list(PROCEDIMIENTOS)

    async def registrar_dictamen(self, dictamen: Dictamen) -> str | None:
        # Sin Notion no hay donde escribir. El dictamen ya quedo en Postgres.
        return None
