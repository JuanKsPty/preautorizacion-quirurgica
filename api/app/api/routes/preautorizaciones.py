"""
La evaluacion.

Dos caminos al mismo veredicto:

  POST /preautorizaciones/evaluar  el agente completo, en streaming (SSE).
  POST /preautorizaciones/reglas   solo el motor de reglas, respuesta JSON.

El segundo existe porque el enunciado del reto se juega en el enlace publico: si
la clave de IA falla o se agota, el sistema tiene que seguir emitiendo un
dictamen correcto — con la redaccion mas seca, pero con el mismo veredicto y las
mismas cifras. Las reglas son puras, asi que cuesta veinte lineas.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import col, select

from app.agente import ejecutor
from app.agente.herramientas import EstadoEjecucion, emparejar_por_texto
from app.api.sse import CABECERAS_SSE, evento, latido
from app.core.config import settings
from app.core.deps import SessionDep
from app.dominio.esquemas import Dictamen, InformeMedico, Poliza, Procedimiento
from app.dominio.financiero import calcular_desglose
from app.dominio.reglas import construir_expediente
from app.dominio.veredicto import construir_chequeos, decidir
from app.models import Preautorizacion, PreautorizacionPublic
from app.repositorios.fabrica import obtener_repositorio

logger = logging.getLogger("app.preautorizaciones")

router = APIRouter(prefix="/preautorizaciones", tags=["preautorización"])


class SolicitudEvaluacion(BaseModel):
    codigo_informe: str = Field(min_length=3, max_length=40)
    # Opcional: si no viene, se toma la poliza que declara el informe.
    numero_poliza: str | None = Field(default=None, max_length=40)


def folio_de(codigo_informe: str) -> str:
    """`INF-2026-0031` -> `PA-2026-0031`. Determinista y legible en voz alta."""
    return "PA-" + codigo_informe.removeprefix("INF-")


async def _cargar_caso(
    solicitud: SolicitudEvaluacion,
) -> tuple[Poliza, InformeMedico, list[Procedimiento]]:
    """
    Lee el expediente completo ANTES de arrancar el agente.

    Asi las herramientas del bucle son funciones puras sobre este snapshot: cero
    red mientras el modelo trabaja. Ademas, un informe o una poliza que no
    existen se responden con un 404 de verdad, y no como un evento de error a
    mitad de un stream ya abierto.
    """
    repositorio = obtener_repositorio()
    informe = await repositorio.obtener_informe(solicitud.codigo_informe)
    if informe is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No existe el informe médico {solicitud.codigo_informe}",
        )

    numero = solicitud.numero_poliza or informe.numero_poliza
    poliza = await repositorio.obtener_poliza(numero)
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la póliza {numero}")

    catalogo = await repositorio.listar_procedimientos()
    if not catalogo:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El catálogo de procedimientos está vacío: no se puede evaluar.",
        )
    return poliza, informe, catalogo


def _guardar(
    session: SessionDep, dictamen: Dictamen, ms_total: int, notion_url: str | None
) -> None:
    """Bitacora. Best-effort: el veredicto ya se transmitio al navegador."""
    desglose = dictamen.desglose
    try:
        session.add(
            Preautorizacion(
                folio=dictamen.folio,
                veredicto=dictamen.veredicto,
                numero_poliza=dictamen.numero_poliza,
                codigo_informe=dictamen.codigo_informe,
                paciente=dictamen.paciente,
                cpt=dictamen.cpt_identificado,
                procedimiento=dictamen.procedimiento_identificado,
                monto_cotizado=desglose.monto_cotizado if desglose else 0.0,
                cubierto_aseguradora=desglose.cubierto_aseguradora if desglose else 0.0,
                a_cargo_paciente=desglose.a_cargo_paciente if desglose else 0.0,
                ms_total=ms_total,
                origen_datos=settings.origen_datos,
                notion_url=notion_url,
                dictamen=dictamen.model_dump(mode="json"),
            )
        )
        session.commit()
    except Exception:
        logger.exception("No se pudo guardar el dictamen %s", dictamen.folio)
        session.rollback()


@router.post("/evaluar", summary="Evaluar una solicitud (agente completo, streaming SSE)")
async def evaluar(solicitud: SolicitudEvaluacion, session: SessionDep) -> StreamingResponse:
    """
    Transmite el trabajo del agente en vivo: su razonamiento, cada herramienta
    con sus argumentos y su resultado, y al final el dictamen.

    Que el proceso se vea es parte del producto: un dictamen de seguros sin traza
    no es auditable, y el evaluador tiene que poder comprobar de donde sale cada
    numero.
    """
    if not settings.ia_habilitada:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Falta ANTHROPIC_API_KEY. Mientras tanto, POST /api/preautorizaciones/reglas "
            "resuelve el caso con el motor de reglas.",
        )

    poliza, informe, catalogo = await _cargar_caso(solicitud)
    estado = EstadoEjecucion(
        folio=folio_de(informe.codigo),
        poliza=poliza,
        informe=informe,
        catalogo=catalogo,
    )

    async def generar() -> AsyncGenerator[str]:
        # El agente empuja a una cola y el generador la vacia con timeout: asi
        # los latidos salen aunque el modelo lleve medio minuto pensando, y
        # ningun proxy corta la conexion por inactividad.
        cola: asyncio.Queue[dict | None] = asyncio.Queue()

        async def bombear() -> None:
            try:
                async with asyncio.timeout(settings.agente_timeout_segundos):
                    async for suceso in ejecutor.ejecutar(estado):
                        await cola.put(suceso)
            except TimeoutError:
                await cola.put(
                    {
                        "tipo": "error",
                        "codigo": "TIEMPO_AGOTADO",
                        "mensaje": (
                            f"La evaluación superó {settings.agente_timeout_segundos} segundos."
                        ),
                    }
                )
            except Exception as error:  # el stream nunca muere en silencio
                logger.exception("Fallo del agente en %s", estado.folio)
                await cola.put({"tipo": "error", "codigo": "INTERNO", "mensaje": str(error)})
            finally:
                await cola.put(None)

        tarea = asyncio.create_task(bombear())
        ms_total = 0
        try:
            yield evento(
                {
                    "tipo": "inicio",
                    "folio": estado.folio,
                    "modelo": settings.anthropic_model,
                    "esfuerzo": settings.anthropic_effort,
                    "origen_datos": settings.origen_datos,
                    "caso": {
                        "codigo_informe": informe.codigo,
                        "numero_poliza": poliza.numero,
                        "paciente": informe.paciente,
                        "hospital": informe.hospital,
                    },
                }
            )
            while True:
                try:
                    suceso = await asyncio.wait_for(
                        cola.get(), timeout=settings.sse_latido_segundos
                    )
                except TimeoutError:
                    yield latido()
                    continue
                if suceso is None:
                    break
                if suceso.get("tipo") == "dictamen":
                    ms_total = int(suceso.get("ms_total", 0))
                yield evento(suceso)
        finally:
            tarea.cancel()
            if estado.dictamen is not None:
                url = None
                try:
                    url = await obtener_repositorio().registrar_dictamen(estado.dictamen)
                except Exception:
                    logger.exception("No se pudo escribir el dictamen en Notion")
                _guardar(session, estado.dictamen, ms_total, url)
            yield evento({"tipo": "fin", "folio": estado.folio, "veredicto": estado.veredicto})

    return StreamingResponse(generar(), media_type="text/event-stream", headers=CABECERAS_SSE)


@router.post(
    "/reglas",
    response_model=Dictamen,
    summary="Evaluar solo con el motor de reglas (sin IA)",
)
async def evaluar_con_reglas(solicitud: SolicitudEvaluacion, session: SessionDep) -> Dictamen:
    """
    El mismo veredicto sin pasar por el modelo.

    El procedimiento se identifica con el emparejador determinista sobre el texto
    del informe, en vez de con el mapeo semantico del modelo.

    LIMITE IMPORTANTE: por este camino no se detectan preexistencias. Descubrir
    que el relato clinico situa un padecimiento ANTES del inicio de la poliza
    exige leer y fechar prosa, y eso no lo hace una regla: es justamente el
    trabajo del modelo. Por eso el informe INF-2026-0035 sale APROBADO aqui y
    REVISION_MEDICA con el agente completo. No es una inconsistencia — es la
    medida de lo que aporta la IA sobre el motor de reglas.
    """
    poliza, informe, catalogo = await _cargar_caso(solicitud)

    emparejado = emparejar_por_texto(catalogo, informe.texto)
    if emparejado is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El motor de reglas no pudo identificar el procedimiento en el informe. "
            "Este caso necesita el agente completo.",
        )
    procedimiento, _ = emparejado

    expediente = construir_expediente(poliza, procedimiento, informe)
    desglose = (
        calcular_desglose(poliza, procedimiento, informe.monto_cotizado)
        if expediente.cobertura.cubierto
        else None
    )
    veredicto, motivos = decidir(expediente, desglose)
    chequeos = construir_chequeos(expediente, desglose)

    dictamen = Dictamen(
        folio=folio_de(informe.codigo),
        veredicto=veredicto,
        resumen=motivos[0] if motivos else "Resolución emitida por el motor de reglas.",
        numero_poliza=poliza.numero,
        codigo_informe=informe.codigo,
        paciente=informe.paciente,
        cpt_identificado=procedimiento.cpt,
        procedimiento_identificado=procedimiento.nombre,
        motivos=motivos,
        documentos_faltantes=expediente.documentos.faltantes,
        chequeos=chequeos,
        desglose=desglose,
        carta_paciente=" ".join(motivos),
        justificacion_tecnica=" ".join(c.detalle for c in chequeos),
    )
    _guardar(session, dictamen, 0, None)
    return dictamen


@router.get(
    "",
    response_model=list[PreautorizacionPublic],
    summary="Historial de dictámenes emitidos",
)
def listar_dictamenes(session: SessionDep, limite: int = 50) -> Sequence[Preautorizacion]:
    consulta = (
        select(Preautorizacion)
        .order_by(col(Preautorizacion.created_at).desc())
        .limit(min(limite, 200))
    )
    return session.exec(consulta).all()
