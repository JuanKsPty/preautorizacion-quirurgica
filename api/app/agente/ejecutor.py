"""
El bucle agentico.

Es un bucle manual y no el `tool_runner` del SDK por tres razones concretas:
hace falta un evento SSE por cada delta de razonamiento y por cada llamada a
herramienta (el runner itera por mensaje completo); hace falta poder cambiar
`tool_choice` a mitad de la ejecucion para escalar; y el runner es beta, una
dependencia menos que se puede romper el dia de la demo.

El generador emite diccionarios de evento; la ruta los convierte en SSE y les
intercala latidos. Garantias del contrato: exactamente un evento `fin`, siempre
en un `finally`, y un `error` siempre antes de el.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import anthropic

from app.agente.herramientas import (
    HERRAMIENTAS,
    ErrorHerramienta,
    EstadoEjecucion,
    dinero,
    ejecutar_herramienta,
)
from app.agente.prompt import CARTA_RESPALDO, PROMPT_SISTEMA, RECORDATORIO_DICTAMEN
from app.core.config import settings
from app.dominio.esquemas import Dictamen

logger = logging.getLogger("app.agente")

_cliente: anthropic.AsyncAnthropic | None = None


def obtener_cliente() -> anthropic.AsyncAnthropic:
    """Un solo cliente por proceso: reutiliza el pool de conexiones."""
    global _cliente
    if _cliente is None:
        _cliente = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _cliente


# Parametros que un modelo o una version de API podria rechazar. Si el
# proveedor devuelve un 400 nombrando uno de ellos, se reintenta sin los
# opcionales antes de rendirse: es preferible un agente sin razonamiento
# transmitido que ningun agente.
OPCIONALES = ("thinking", "output_config", "effort", "cache_control", "display")


def _parametro_no_soportado(error: anthropic.BadRequestError) -> bool:
    mensaje = str(error).lower()
    return any(clave in mensaje for clave in OPCIONALES)


def _peticion(
    estado: EstadoEjecucion,
    mensajes: list[dict[str, Any]],
    numero: int,
    maximo: int,
    compatibilidad: bool,
) -> dict[str, Any]:
    """Arma la peticion. En modo compatibilidad va sin los parametros opcionales."""
    peticion: dict[str, Any] = {
        "model": settings.anthropic_model,
        "max_tokens": settings.anthropic_max_tokens,
        "tools": HERRAMIENTAS,
        "messages": mensajes,
    }

    if compatibilidad:
        peticion["system"] = PROMPT_SISTEMA
    else:
        # El prompt va primero y cacheado: es el prefijo estable de cada vuelta.
        peticion["system"] = [
            {
                "type": "text",
                "text": PROMPT_SISTEMA,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        peticion["thinking"] = {"type": "adaptive", "display": "summarized"}
        peticion["output_config"] = {"effort": settings.anthropic_effort}

    # En las dos ultimas vueltas se fuerza la siguiente herramienta del riel.
    # Forzar `emitir_dictamen` sin haber evaluado solo produciria un error, asi
    # que se escala en orden.
    if numero > maximo - 2:
        obligatoria = _siguiente_obligatoria(estado)
        if obligatoria:
            peticion["tool_choice"] = {"type": "tool", "name": obligatoria}

    return peticion


def _primer_mensaje(estado: EstadoEjecucion) -> str:
    return (
        f"Resuelve la solicitud de pre-autorización {estado.folio}.\n\n"
        f"Informe médico: {estado.informe.codigo}\n"
        f"Póliza: {estado.poliza.numero}\n"
        f"Paciente: {estado.informe.paciente}\n"
        f"Hospital: {estado.informe.hospital}\n"
        f"Fecha propuesta de cirugía: {estado.informe.fecha_cirugia_propuesta:%d/%m/%Y}\n\n"
        "Empieza consultando la póliza y el informe."
    )


def _siguiente_obligatoria(estado: EstadoEjecucion) -> str | None:
    """El riel de dependencias, para escalar en orden y no forzar algo imposible."""
    if estado.analisis is None:
        return "registrar_analisis_clinico"
    if estado.procedimiento is None:
        return "seleccionar_procedimiento"
    if estado.veredicto is None:
        return "evaluar_expediente"
    if estado.dictamen is None:
        return "emitir_dictamen"
    return None


def dictamen_respaldo(estado: EstadoEjecucion) -> Dictamen | None:
    """
    Dictamen armado en Python desde el estado ya calculado.

    Se usa si el modelo nunca llega a emitir uno. El veredicto y las cifras son
    los correctos; solo la redaccion es de plantilla. La demo nunca termina sin
    resolucion.
    """
    if estado.veredicto is None:
        return None

    partes = [CARTA_RESPALDO.get(estado.veredicto, ""), *estado.motivos]
    if estado.expediente and estado.expediente.documentos.faltantes:
        partes.append(
            "Documentos pendientes: " + ", ".join(estado.expediente.documentos.faltantes) + "."
        )
    if estado.desglose:
        partes.append(
            f"La aseguradora cubriría {dinero(estado.desglose.cubierto_aseguradora)} "
            f"y quedarían {dinero(estado.desglose.a_cargo_paciente)} a cargo del paciente."
        )

    return Dictamen(
        folio=estado.folio,
        veredicto=estado.veredicto,
        resumen=estado.motivos[0] if estado.motivos else "Resolución emitida por las reglas.",
        numero_poliza=estado.poliza.numero,
        codigo_informe=estado.informe.codigo,
        paciente=estado.informe.paciente,
        cpt_identificado=estado.procedimiento.cpt if estado.procedimiento else None,
        procedimiento_identificado=(estado.procedimiento.nombre if estado.procedimiento else None),
        cie10_identificado=estado.analisis.cie10 if estado.analisis else None,
        motivos=estado.motivos,
        documentos_faltantes=(estado.expediente.documentos.faltantes if estado.expediente else []),
        chequeos=estado.chequeos,
        desglose=estado.desglose,
        carta_paciente=" ".join(partes),
        justificacion_tecnica=(
            "Dictamen generado por el motor de reglas sin redacción del modelo. "
            + " ".join(c.detalle for c in estado.chequeos)
        ),
    )


async def _rescatar(estado: EstadoEjecucion, arranque: float) -> AsyncGenerator[dict[str, Any]]:
    """
    Entrega el dictamen que se pueda armar despues de un fallo del proveedor.

    Si el modelo ya habia llegado a `evaluar_expediente`, el veredicto y las
    cifras estan calculados y son correctos: seria absurdo tirarlos porque la
    llamada siguiente fallara. Solo se pierde la redaccion.
    """
    if estado.dictamen is not None or estado.veredicto is None:
        return
    respaldo = dictamen_respaldo(estado)
    if respaldo is None:
        return
    estado.dictamen = respaldo
    yield {
        "tipo": "aviso",
        "mensaje": (
            "El proveedor falló despues de aplicar las reglas: el dictamen se "
            "entrega con la plantilla de respaldo, con el veredicto y las cifras "
            "ya calculados."
        ),
    }
    yield {
        "tipo": "dictamen",
        "dictamen": estado.dictamen.model_dump(mode="json"),
        "ms_total": round((time.monotonic() - arranque) * 1000),
    }


async def ejecutar(estado: EstadoEjecucion) -> AsyncGenerator[dict[str, Any]]:
    """Corre el agente sobre un caso ya cargado y va emitiendo eventos."""
    arranque = time.monotonic()
    cliente = obtener_cliente()
    maximo = settings.agente_max_iteraciones

    mensajes: list[dict[str, Any]] = [{"role": "user", "content": _primer_mensaje(estado)}]

    try:
        vueltas = 0
        compatibilidad = False
        while vueltas < maximo:
            numero = vueltas + 1
            peticion = _peticion(estado, mensajes, numero, maximo, compatibilidad)

            try:
                stream_ctx = cliente.messages.stream(**peticion)
            except anthropic.BadRequestError as error:
                if compatibilidad or not _parametro_no_soportado(error):
                    raise
                compatibilidad = True
                yield {
                    "tipo": "aviso",
                    "mensaje": (
                        "El proveedor rechazó un parámetro opcional; se reintenta "
                        "sin razonamiento transmitido ni control de esfuerzo."
                    ),
                }
                continue

            iteracion = numero
            async with stream_ctx as stream:
                async for evento in stream:
                    if evento.type != "content_block_delta":
                        continue
                    if evento.delta.type == "thinking_delta":
                        yield {"tipo": "razonamiento", "texto": evento.delta.thinking}
                    elif evento.delta.type == "text_delta":
                        yield {"tipo": "comentario", "texto": evento.delta.text}
                respuesta = await stream.get_final_message()

            # El contenido del asistente se devuelve VERBATIM: los bloques de
            # razonamiento viajan firmados junto al tool_use y reconstruirlos da 400.
            mensajes.append({"role": "assistant", "content": respuesta.content})

            if respuesta.stop_reason == "max_tokens":
                yield {
                    "tipo": "aviso",
                    "mensaje": "La respuesta del modelo se truncó; se continúa la evaluación.",
                }

            llamadas = [b for b in respuesta.content if b.type == "tool_use"]

            vueltas = numero

            if not llamadas:
                if estado.dictamen is not None:
                    break
                mensajes.append({"role": "user", "content": RECORDATORIO_DICTAMEN})
                continue

            resultados: list[dict[str, Any]] = []
            for llamada in llamadas:
                argumentos = dict(llamada.input or {})
                yield {
                    "tipo": "herramienta",
                    "fase": "inicio",
                    "id": llamada.id,
                    "nombre": llamada.name,
                    "iteracion": iteracion,
                    "argumentos": argumentos,
                }
                inicio = time.monotonic()
                try:
                    salida = await ejecutar_herramienta(llamada.name, argumentos, estado)
                    resultados.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": llamada.id,
                            "content": json.dumps(salida, ensure_ascii=False, default=str),
                        }
                    )
                    yield {
                        "tipo": "herramienta",
                        "fase": "fin",
                        "id": llamada.id,
                        "nombre": llamada.name,
                        "ok": True,
                        "ms": round((time.monotonic() - inicio) * 1000),
                        "resultado": salida,
                    }
                    # En cuanto hay chequeos, la UI puede pintarlos sin esperar.
                    if llamada.name == "evaluar_expediente":
                        yield {
                            "tipo": "chequeos",
                            "veredicto": estado.veredicto,
                            "chequeos": [c.model_dump() for c in estado.chequeos],
                            "desglose": (estado.desglose.model_dump() if estado.desglose else None),
                        }
                except ErrorHerramienta as error:
                    resultados.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": llamada.id,
                            "content": str(error),
                            "is_error": True,
                        }
                    )
                    yield {
                        "tipo": "herramienta",
                        "fase": "fin",
                        "id": llamada.id,
                        "nombre": llamada.name,
                        "ok": False,
                        "ms": round((time.monotonic() - inicio) * 1000),
                        "error": str(error),
                    }
                except Exception:
                    logger.exception("Fallo inesperado en la herramienta %s", llamada.name)
                    resultados.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": llamada.id,
                            "content": "Error interno de la herramienta.",
                            "is_error": True,
                        }
                    )
                    yield {
                        "tipo": "herramienta",
                        "fase": "fin",
                        "id": llamada.id,
                        "nombre": llamada.name,
                        "ok": False,
                        "ms": round((time.monotonic() - inicio) * 1000),
                        "error": "Error interno de la herramienta.",
                    }

            mensajes.append({"role": "user", "content": resultados})

            if estado.dictamen is not None:
                break

        if estado.dictamen is None:
            respaldo = dictamen_respaldo(estado)
            if respaldo is not None:
                estado.dictamen = respaldo
                yield {
                    "tipo": "aviso",
                    "mensaje": (
                        "El modelo no emitió el dictamen; se redactó con la plantilla "
                        "de respaldo. El veredicto y las cifras son los calculados."
                    ),
                }
            else:
                yield {
                    "tipo": "error",
                    "codigo": "SIN_DICTAMEN",
                    "mensaje": (f"El agente no llegó a una resolución en {maximo} iteraciones."),
                }

        if estado.dictamen is not None:
            yield {
                "tipo": "dictamen",
                "dictamen": estado.dictamen.model_dump(mode="json"),
                "ms_total": round((time.monotonic() - arranque) * 1000),
            }

    except anthropic.APIStatusError as error:
        yield {
            "tipo": "error",
            "codigo": "PROVEEDOR",
            "mensaje": f"El proveedor de IA respondió con código {error.status_code}.",
        }
        async for suceso in _rescatar(estado, arranque):
            yield suceso
    except anthropic.APIConnectionError:
        yield {
            "tipo": "error",
            "codigo": "CONEXION",
            "mensaje": "No se pudo conectar con el proveedor de IA.",
        }
        async for suceso in _rescatar(estado, arranque):
            yield suceso
