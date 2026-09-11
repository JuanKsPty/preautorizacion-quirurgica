"""
Prerrelleno del formulario de alta a partir del informe en texto libre.

No requiere Notion a proposito: solo lee texto y llama al modelo. Asi la
interaccion que mejor demuestra el producto sigue funcionando aunque Notion este
caido — lo unico que se apaga entonces son los botones de Guardar.

Y tampoco requiere clave de IA para responder: sin ella devuelve lo que se puede
sacar del texto con expresiones regulares. Un formulario que se niega a abrirse
es peor demostracion que uno que abre a medias.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agente.extraccion import RespuestaExtraccion, extraer
from app.repositorios.fabrica import obtener_repositorio

router = APIRouter(prefix="/informes", tags=["expediente"])


class SolicitudExtraccion(BaseModel):
    texto: str = Field(min_length=40, max_length=40_000)


@router.post(
    "/extraer",
    response_model=RespuestaExtraccion,
    summary="Leer un informe en texto libre y proponer los campos del formulario",
)
async def extraer_informe(solicitud: SolicitudExtraccion) -> RespuestaExtraccion:
    # El catalogo sirve para dos cosas: darle al modelo los nombres canonicos de
    # documento, y sugerir el CPT con el emparejador determinista.
    catalogo = await obtener_repositorio().listar_procedimientos()
    return await extraer(solicitud.texto, catalogo)
