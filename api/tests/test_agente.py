"""
El bucle agentico completo, con un cliente de Anthropic falso.

Fija el contrato del stream (que eventos salen y en que orden), comprueba que
los parametros que se le mandan al modelo son los correctos, y verifica los dos
caminos de degradacion: sin clave de IA, y con un modelo que nunca emite el
dictamen.
"""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agente import ejecutor
from app.core.config import settings

# --------------------------------------------------------- cliente de mentira


def bloque_texto(texto: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=texto)


def bloque_tool(id_: str, nombre: str, argumentos: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id_, name=nombre, input=argumentos)


def delta_razonamiento(texto: str) -> SimpleNamespace:
    return SimpleNamespace(
        type="content_block_delta", delta=SimpleNamespace(type="thinking_delta", thinking=texto)
    )


def delta_texto(texto: str) -> SimpleNamespace:
    return SimpleNamespace(
        type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=texto)
    )


class _StreamFalso:
    def __init__(self, eventos: list, mensaje: SimpleNamespace) -> None:
        self._eventos = eventos
        self._mensaje = mensaje

    async def __aenter__(self) -> "_StreamFalso":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    def __aiter__(self):
        async def generar():
            for evento in self._eventos:
                yield evento

        return generar()

    async def get_final_message(self) -> SimpleNamespace:
        return self._mensaje


class _MensajesFalsos:
    def __init__(self, turnos: list[tuple[list, SimpleNamespace]]) -> None:
        self._turnos = turnos
        self.peticiones: list[dict] = []

    def stream(self, **kwargs) -> _StreamFalso:
        self.peticiones.append(kwargs)
        indice = min(len(self.peticiones) - 1, len(self._turnos) - 1)
        eventos, mensaje = self._turnos[indice]
        return _StreamFalso(eventos, mensaje)


class _ClienteFalso:
    def __init__(self, turnos: list[tuple[list, SimpleNamespace]]) -> None:
        self.messages = _MensajesFalsos(turnos)


def guion_completo() -> list[tuple[list, SimpleNamespace]]:
    """Un modelo que hace las cosas bien, en cinco turnos."""
    return [
        (
            [delta_razonamiento("Necesito la póliza y el informe.")],
            SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    bloque_tool("t1", "consultar_poliza", {}),
                    bloque_tool("t2", "consultar_informe", {}),
                ],
            ),
        ),
        (
            [delta_texto("Busco el procedimiento en el catálogo.")],
            SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    bloque_tool(
                        "t3", "buscar_procedimiento", {"descripcion": "cirugía de vesícula"}
                    )
                ],
            ),
        ),
        (
            [],
            SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    bloque_tool(
                        "t4",
                        "registrar_analisis_clinico",
                        {
                            "diagnostico_principal": "Colelitiasis con colecistitis crónica",
                            "cie10": "K80.1",
                            "procedimiento_descrito": "extirpación de vesícula por laparoscopía",
                            "lateralidad": "no_aplica",
                            "urgencia": "electiva",
                            "condiciones_previas_detectadas": [],
                            "informe_sustenta_procedimiento": True,
                            "observaciones": "",
                        },
                    ),
                    bloque_tool(
                        "t5",
                        "seleccionar_procedimiento",
                        {"cpt": "47562", "justificacion": "mapeo directo"},
                    ),
                ],
            ),
        ),
        (
            [],
            SimpleNamespace(
                stop_reason="tool_use",
                content=[bloque_tool("t6", "evaluar_expediente", {})],
            ),
        ),
        (
            [],
            SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    bloque_tool(
                        "t7",
                        "emitir_dictamen",
                        {
                            "veredicto": "APROBADO",
                            "resumen": "Procedimiento aprobado.",
                            "carta_paciente": "Su cirugía fue aprobada. Puede coordinar la fecha.",
                            "justificacion_tecnica": "CPT 47562, CIE-10 K80.1, carencia cumplida.",
                        },
                    )
                ],
            ),
        ),
        # Turno de cierre: el modelo ya no pide nada mas.
        ([], SimpleNamespace(stop_reason="end_turn", content=[bloque_texto("Listo.")])),
    ]


def leer_eventos(texto: str) -> list[dict]:
    """Trocea el cuerpo SSE en los diccionarios de evento, ignorando latidos."""
    eventos = []
    for bloque in texto.split("\n\n"):
        for linea in bloque.split("\n"):
            if linea.startswith("data:"):
                eventos.append(json.loads(linea[len("data:") :].strip()))
    return eventos


# ------------------------------------------------------------------- el camino


def test_la_evaluacion_completa_emite_el_dictamen(client: TestClient, monkeypatch):
    falso = _ClienteFalso(guion_completo())
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    monkeypatch.setattr(ejecutor, "obtener_cliente", lambda: falso)

    respuesta = client.post(
        "/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-2026-0031"}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    # Sin esto, nginx bufferea el stream y se ve congelado.
    assert respuesta.headers["x-accel-buffering"] == "no"

    eventos = leer_eventos(respuesta.text)
    tipos = [e["tipo"] for e in eventos]

    assert tipos[0] == "inicio"
    assert tipos[-1] == "fin"
    # Exactamente un fin y un dictamen: el contrato del que depende el frontend.
    assert tipos.count("fin") == 1
    assert tipos.count("dictamen") == 1
    assert "razonamiento" in tipos
    assert "chequeos" in tipos

    dictamen = next(e["dictamen"] for e in eventos if e["tipo"] == "dictamen")
    assert dictamen["veredicto"] == "APROBADO"
    assert dictamen["cpt_identificado"] == "47562"
    assert dictamen["cie10_identificado"] == "K80.1"
    assert len(dictamen["chequeos"]) == 6
    assert dictamen["desglose"]["cubierto_aseguradora"] == 4896.0


def test_se_le_mandan_al_modelo_los_parametros_correctos(client: TestClient, monkeypatch):
    falso = _ClienteFalso(guion_completo())
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    monkeypatch.setattr(ejecutor, "obtener_cliente", lambda: falso)

    client.post("/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-2026-0031"})

    primera = falso.messages.peticiones[0]
    assert primera["model"] == settings.anthropic_model
    # Razonamiento adaptativo y resumido: es lo que permite transmitirlo.
    assert primera["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert primera["output_config"] == {"effort": settings.anthropic_effort}
    assert primera["max_tokens"] >= 8192
    # El prompt de sistema va cacheado: es el prefijo estable de cada vuelta.
    assert primera["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert {h["name"] for h in primera["tools"]} == {
        "consultar_poliza",
        "consultar_informe",
        "buscar_procedimiento",
        "registrar_analisis_clinico",
        "seleccionar_procedimiento",
        "evaluar_expediente",
        "emitir_dictamen",
    }


def test_el_dictamen_queda_en_la_bitacora(client: TestClient, monkeypatch):
    falso = _ClienteFalso(guion_completo())
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    monkeypatch.setattr(ejecutor, "obtener_cliente", lambda: falso)

    client.post("/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-2026-0031"})

    historial = client.get("/api/preautorizaciones").json()
    assert len(historial) == 1
    assert historial[0]["folio"] == "PA-2026-0031"
    assert historial[0]["veredicto"] == "APROBADO"
    assert historial[0]["cpt"] == "47562"


# ------------------------------------------------------------- degradaciones


def test_sin_clave_de_ia_se_responde_503_y_se_ofrece_el_motor_de_reglas(
    client: TestClient, monkeypatch
):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    respuesta = client.post(
        "/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-2026-0031"}
    )
    assert respuesta.status_code == 503
    detalle = respuesta.json()["detail"]
    assert "ANTHROPIC_API_KEY" in detalle
    assert "reglas" in detalle


def test_si_el_modelo_nunca_emite_el_dictamen_se_usa_la_plantilla_de_respaldo(
    client: TestClient, monkeypatch
):
    """
    La demo nunca termina sin veredicto. Si el modelo se queda dando vueltas, el
    dictamen se arma en Python desde las reglas ya calculadas.
    """
    guion = guion_completo()[:4]  # llega a evaluar_expediente y ahi se queda
    guion.append(([], SimpleNamespace(stop_reason="end_turn", content=[bloque_texto("Mmm.")])))
    falso = _ClienteFalso(guion)
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    monkeypatch.setattr(ejecutor, "obtener_cliente", lambda: falso)
    monkeypatch.setattr(settings, "agente_max_iteraciones", 6)

    respuesta = client.post(
        "/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-2026-0031"}
    )
    eventos = leer_eventos(respuesta.text)
    tipos = [e["tipo"] for e in eventos]

    assert "aviso" in tipos
    assert "dictamen" in tipos
    dictamen = next(e["dictamen"] for e in eventos if e["tipo"] == "dictamen")
    # El veredicto y las cifras son los correctos; solo la redaccion es seca.
    assert dictamen["veredicto"] == "APROBADO"
    assert dictamen["desglose"]["cubierto_aseguradora"] == 4896.0


def test_un_informe_que_no_existe_da_404_antes_de_abrir_el_stream(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")
    respuesta = client.post(
        "/api/preautorizaciones/evaluar", json={"codigo_informe": "INF-NO-EXISTE"}
    )
    assert respuesta.status_code == 404
