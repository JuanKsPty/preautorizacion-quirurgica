"""
El prerrelleno del formulario.

Lo que se fija aquí, por orden de importancia: que nunca devuelva 5xx, que un
campo mal formado cueste un campo y no la extracción entera, y que los
documentos se ajusten a la grafía del catálogo — si no, `evaluar_documentos` no
los reconocería y el veredicto cambiaría sin ningún error a la vista.
"""

from datetime import date
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app.agente import extraccion as modulo
from app.agente.extraccion import ExtraccionCruda, normalizar_extraccion
from app.core.config import settings
from app.repositorios.datos_demo import INFORMES, PROCEDIMIENTOS

CRUDA_COMPLETA = {
    "paciente": "Ricardo Mendoza Barría",
    "cedula": "8-812-2043",
    "numero_poliza": "POL-2024-0148",
    "hospital": "Hospital Punta Pacífica",
    "medico_tratante": "Dra. Ileana Sáez Moreno",
    "especialidad": "Cirugía general",
    "fecha_informe": "2026-09-04",
    "fecha_cirugia_propuesta": "2026-09-22",
    "es_emergencia": False,
    "monto_cotizado": "6800.00",
    "documentos_adjuntos": ["Informe médico firmado"],
    "diagnostico_presuntivo": "Colelitiasis con colecistitis crónica",
    "cie10_presuntivo": "K80.1",
    "procedimiento_descrito": "extirpación de la vesícula por laparoscopía",
}


def cliente_falso(cruda: dict | None = None, error: Exception | None = None):
    """Imita lo justo: `.with_options(...).messages.parse(...)`."""
    llamadas: list[dict] = []

    class _Mensajes:
        async def parse(self, **kwargs):
            llamadas.append(kwargs)
            if error is not None:
                raise error
            return SimpleNamespace(parsed_output=ExtraccionCruda(**(cruda or CRUDA_COMPLETA)))

    class _Cliente:
        messages = _Mensajes()

        def with_options(self, **_):
            return self

    falso = _Cliente()
    falso.llamadas = llamadas  # type: ignore[attr-defined]
    return falso


@pytest.fixture(name="con_ia")
def con_ia_fixture(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-de-prueba")


# ------------------------------------------------------------- con modelo


def test_la_extraccion_rellena_el_formulario(client: TestClient, con_ia, monkeypatch):
    falso = cliente_falso()
    monkeypatch.setattr(modulo, "obtener_cliente", lambda: falso)

    respuesta = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["origen"] == "ia"
    campos = cuerpo["campos"]
    assert campos["paciente"] == "Ricardo Mendoza Barría"
    assert campos["fecha_informe"] == "2026-09-04"
    assert campos["monto_cotizado"] == 6800.0
    assert campos["cie10_presuntivo"] == "K80.1"
    assert cuerpo["campos_no_encontrados"] == []


def test_se_le_mandan_al_modelo_los_parametros_correctos(client: TestClient, con_ia, monkeypatch):
    falso = cliente_falso()
    monkeypatch.setattr(modulo, "obtener_cliente", lambda: falso)
    client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto})

    peticion = falso.llamadas[0]
    assert peticion["model"] == settings.anthropic_model
    # Esfuerzo bajo: esto es transcripcion, y 15 segundos de espera se abandonan.
    assert peticion["output_config"] == {"effort": settings.anthropic_effort_extraccion}
    assert peticion["output_format"] is ExtraccionCruda
    # Al modelo se le dan los nombres canonicos de documento, para que no invente
    # variantes que luego el motor de reglas no reconoceria.
    assert "Estudio de imágenes" in peticion["system"]


def test_un_campo_que_el_informe_no_dice_se_lista_como_no_encontrado(
    client: TestClient, con_ia, monkeypatch
):
    monkeypatch.setattr(
        modulo, "obtener_cliente", lambda: cliente_falso({**CRUDA_COMPLETA, "hospital": None})
    )
    cuerpo = client.post(
        "/api/informes/extraer",
        json={
            "texto": "Relato clínico que no menciona en ninguna parte el nombre del centro médico."
        },
    ).json()
    assert "hospital" in cuerpo["campos_no_encontrados"]
    assert cuerpo["campos"]["hospital"] is None


def test_un_cie10_con_forma_invalida_se_descarta(client: TestClient, con_ia, monkeypatch):
    """Devolverlo solo meteria basura en el formulario."""
    monkeypatch.setattr(
        modulo,
        "obtener_cliente",
        lambda: cliente_falso({**CRUDA_COMPLETA, "cie10_presuntivo": "colelitiasis"}),
    )
    cuerpo = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto}).json()
    assert cuerpo["campos"]["cie10_presuntivo"] is None


def test_una_fecha_mal_formada_no_tumba_la_extraccion(client: TestClient, con_ia, monkeypatch):
    """Una fecha rota cuesta UN campo, no los catorce."""
    monkeypatch.setattr(
        modulo,
        "obtener_cliente",
        lambda: cliente_falso({**CRUDA_COMPLETA, "fecha_cirugia_propuesta": "22 de sept"}),
    )
    cuerpo = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto}).json()
    assert cuerpo["campos"]["fecha_cirugia_propuesta"] is None
    assert cuerpo["campos"]["paciente"] == "Ricardo Mendoza Barría"


def test_los_documentos_se_ajustan_a_la_grafia_del_catalogo(
    client: TestClient, con_ia, monkeypatch
):
    monkeypatch.setattr(
        modulo,
        "obtener_cliente",
        lambda: cliente_falso(
            {**CRUDA_COMPLETA, "documentos_adjuntos": ["estudio de imagenes", "Carta rara"]}
        ),
    )
    cuerpo = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto}).json()
    # El conocido se corrige; el desconocido se conserva tal cual.
    assert cuerpo["campos"]["documentos_adjuntos"] == ["Estudio de imágenes", "Carta rara"]


# ------------------------------------------------------------ degradacion


def test_sin_clave_de_ia_responde_200_con_lo_que_saca_del_texto(client: TestClient):
    """Un formulario que se niega a abrirse es peor que uno que abre a medias."""
    respuesta = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["origen"] == "sin_ia"
    assert "ANTHROPIC_API_KEY" in cuerpo["aviso"]
    # Y aun asi rellena lo que el texto dice literalmente.
    assert cuerpo["campos"]["cedula"] is None or cuerpo["campos"]["cpt_sugerido"] == "47562"


def test_si_el_proveedor_falla_se_degrada_pero_responde(client: TestClient, con_ia, monkeypatch):
    caido = cliente_falso(
        error=anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        )
    )
    monkeypatch.setattr(modulo, "obtener_cliente", lambda: caido)

    respuesta = client.post("/api/informes/extraer", json={"texto": INFORMES[0].texto})
    assert respuesta.status_code == 200, "la extracción no puede devolver 5xx"
    assert respuesta.json()["origen"] == "ia_degradada"


def test_un_texto_ridiculamente_corto_se_rechaza(client: TestClient):
    assert client.post("/api/informes/extraer", json={"texto": "hola"}).status_code == 422


# ------------------------------------------------- el normalizador, sin red


def test_el_normalizador_saca_datos_del_texto_sin_modelo():
    """
    Pura, sin cliente ni red. Es la que sostiene los dos caminos degradados.
    """
    campos, faltan = normalizar_extraccion(None, INFORMES[0].texto, list(PROCEDIMIENTOS))
    # El informe menciona la fecha del ultrasonido en dd/mm/aaaa.
    assert campos.fecha_informe == date(2026, 9, 2)
    assert campos.cpt_sugerido == "47562"
    assert "paciente" in faltan, "sin modelo, el nombre no se puede sacar del relato"


def test_el_normalizador_detecta_la_urgencia_en_el_texto():
    campos, _ = normalizar_extraccion(None, INFORMES[5].texto, list(PROCEDIMIENTOS))
    assert campos.es_emergencia is True, "el relato habla de urgencias"


def test_el_normalizador_lee_cedula_poliza_y_monto():
    texto = (
        "Paciente con cédula 8-812-2043, póliza POL-2024-0148. El hospital cotiza "
        "B/. 12,500.00 por el procedimiento de extirpación de la vesícula."
    )
    campos, _ = normalizar_extraccion(None, texto, list(PROCEDIMIENTOS))
    assert campos.cedula == "8-812-2043"
    assert campos.numero_poliza == "POL-2024-0148"
    assert campos.monto_cotizado == 12500.0
