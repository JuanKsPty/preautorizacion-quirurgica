"""
Lectura del expediente: polizas, informes y el catalogo de procedimientos.

El catalogo se expone a proposito. La pantalla de reglas lo muestra tal cual
para que quien evalue el dictamen pueda comprobar que se ajusta a la carencia y
a las exclusiones que estaban publicadas de antemano, en vez de tener que
creerse el resultado.
"""

from fastapi import APIRouter, HTTPException, status

from app.dominio.esquemas import InformeMedico, Poliza, Procedimiento
from app.repositorios.fabrica import obtener_repositorio

router = APIRouter(tags=["expediente"])


@router.get("/polizas", response_model=list[Poliza], summary="Listar pólizas")
async def listar_polizas() -> list[Poliza]:
    return await obtener_repositorio().listar_polizas()


@router.get("/polizas/{numero}", response_model=Poliza, summary="Ver una póliza")
async def ver_poliza(numero: str) -> Poliza:
    poliza = await obtener_repositorio().obtener_poliza(numero)
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la póliza {numero}")
    return poliza


@router.get("/informes", response_model=list[InformeMedico], summary="Listar informes médicos")
async def listar_informes() -> list[InformeMedico]:
    return await obtener_repositorio().listar_informes()


@router.get("/informes/{codigo}", response_model=InformeMedico, summary="Ver un informe médico")
async def ver_informe(codigo: str) -> InformeMedico:
    informe = await obtener_repositorio().obtener_informe(codigo)
    if informe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el informe {codigo}")
    return informe


@router.get(
    "/procedimientos",
    response_model=list[Procedimiento],
    summary="Catálogo de procedimientos con sus carencias y exclusiones",
)
async def listar_procedimientos() -> list[Procedimiento]:
    return await obtener_repositorio().listar_procedimientos()
