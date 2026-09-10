"""
Las reglas deterministas, con fechas reales.

Estas pruebas son la razon por la que el veredicto es defendible: si la
aritmetica de la carencia se rompe, falla aqui y no delante de un evaluador.
"""

from datetime import date

import pytest

from app.dominio.esquemas import Poliza, Procedimiento
from app.dominio.reglas import (
    evaluar_carencia,
    evaluar_cobertura,
    evaluar_documentos,
    evaluar_preexistencia,
    evaluar_vigencia,
)


def poliza(**cambios) -> Poliza:
    base = {
        "numero": "POL-TEST-0001",
        "titular": "Persona de Prueba",
        "cedula": "8-000-0000",
        "plan": "preferente",
        "estado": "vigente",
        "inicio_vigencia": date(2026, 1, 1),
        "fin_vigencia": date(2027, 1, 1),
        "deducible_anual": 500.0,
        "deducible_consumido": 0.0,
        "coaseguro_porcentaje": 20,
        "tope_anual": 50_000.0,
        "tope_consumido": 0.0,
    }
    return Poliza(**(base | cambios))


def procedimiento(**cambios) -> Procedimiento:
    base = {
        "cpt": "99999",
        "nombre": "Procedimiento de prueba",
        "categoria": "Prueba",
        "carencia_dias": {"basico": 180, "preferente": 90, "ejecutivo": 60},
        "cobertura_porcentaje": {"basico": 80, "preferente": 90, "ejecutivo": 100},
        "documentos_requeridos": ["Informe médico firmado", "Copia de cédula"],
    }
    return Procedimiento(**(base | cambios))


# ------------------------------------------------------------------- vigencia


@pytest.mark.parametrize("estado", ["en_mora", "vencida", "cancelada"])
def test_una_poliza_que_no_esta_vigente_nunca_pasa(estado):
    resultado = evaluar_vigencia(poliza(estado=estado), date(2026, 6, 1))
    assert resultado.vigente is False
    assert resultado.estado == estado


def test_la_vigencia_no_cubre_el_dia_siguiente_a_su_fin():
    p = poliza(fin_vigencia=date(2026, 6, 30))
    assert evaluar_vigencia(p, date(2026, 6, 30)).vigente is True
    assert evaluar_vigencia(p, date(2026, 7, 1)).vigente is False


def test_una_cirugia_antes_del_inicio_de_vigencia_no_procede():
    resultado = evaluar_vigencia(poliza(inicio_vigencia=date(2026, 5, 1)), date(2026, 4, 30))
    assert resultado.vigente is False
    assert resultado.estado == "no_iniciada"


# ------------------------------------------------------------------- carencia


def test_la_carencia_se_cumple_exactamente_el_dia_que_toca():
    """El limite exacto: 90 dias de afiliacion frente a 90 exigidos, cumple."""
    p = poliza(inicio_vigencia=date(2026, 1, 1))  # plan preferente: 90 dias
    resultado = evaluar_carencia(p, procedimiento(), date(2026, 4, 1))
    assert resultado.dias_afiliado == 90
    assert resultado.carencia_exigida == 90
    assert resultado.cumple is True
    assert resultado.dias_faltantes == 0


def test_un_dia_antes_de_cumplir_la_carencia_falta_exactamente_un_dia():
    p = poliza(inicio_vigencia=date(2026, 1, 1))
    resultado = evaluar_carencia(p, procedimiento(), date(2026, 3, 31))
    assert resultado.cumple is False
    assert resultado.dias_faltantes == 1
    assert resultado.fecha_habilitacion == date(2026, 4, 1)


def test_la_carencia_exigida_depende_del_plan_contratado():
    inicio = date(2026, 1, 1)
    cirugia = date(2026, 4, 1)  # 90 dias
    proc = procedimiento()
    assert evaluar_carencia(poliza(plan="ejecutivo", inicio_vigencia=inicio), proc, cirugia).cumple
    assert evaluar_carencia(poliza(plan="preferente", inicio_vigencia=inicio), proc, cirugia).cumple
    # El plan basico exige 180: los mismos 90 dias no alcanzan.
    assert not evaluar_carencia(poliza(plan="basico", inicio_vigencia=inicio), proc, cirugia).cumple


def test_una_urgencia_exonera_la_carencia():
    """
    Sin esta excepcion el agente rechazaria una apendicitis aguda, que es
    exactamente el caso en el que un paciente no puede esperar.
    """
    p = poliza(inicio_vigencia=date(2026, 8, 1))
    resultado = evaluar_carencia(p, procedimiento(), date(2026, 8, 15), es_emergencia=True)
    assert resultado.cumple is True
    assert resultado.exonerada_por_emergencia is True
    # Los dias reales se siguen reportando: la exoneracion no borra el dato.
    assert resultado.dias_afiliado == 14
    assert resultado.dias_faltantes == 76


# ------------------------------------------------------------------ cobertura


def test_una_exclusion_absoluta_gana_a_cualquier_plan():
    proc = procedimiento(
        exclusion="cirugía con fines estéticos",
        cobertura_porcentaje={"basico": 100, "preferente": 100, "ejecutivo": 100},
    )
    resultado = evaluar_cobertura(poliza(plan="ejecutivo"), proc)
    assert resultado.excluido is True
    assert resultado.cubierto is False


def test_un_plan_con_cobertura_cero_no_cubre_el_procedimiento():
    proc = procedimiento(cobertura_porcentaje={"basico": 0, "preferente": 50, "ejecutivo": 80})
    assert evaluar_cobertura(poliza(plan="basico"), proc).cubierto is False
    assert evaluar_cobertura(poliza(plan="preferente"), proc).porcentaje == 50


# ------------------------------------------------------------------ documentos


def test_los_documentos_se_comparan_sin_tildes_ni_mayusculas():
    """
    El nombre del documento lo teclea una persona en el hospital: "Copia de
    Cedula" y "Copia de cédula" son el mismo papel.
    """
    resultado = evaluar_documentos(procedimiento(), ["INFORME MEDICO FIRMADO", "Copia de Cedula"])
    assert resultado.completo is True
    assert resultado.faltantes == []


def test_se_reporta_exactamente_que_documento_falta():
    resultado = evaluar_documentos(procedimiento(), ["Informe médico firmado"])
    assert resultado.completo is False
    assert resultado.faltantes == ["Copia de cédula"]


# --------------------------------------------------------------- preexistencia


def test_una_condicion_ya_declarada_no_dispara_revision():
    p = poliza(preexistencias_declaradas=["Hipertensión arterial esencial"])
    resultado = evaluar_preexistencia(p, ["hipertension arterial"])
    assert resultado.hay_indicios is False


def test_una_condicion_no_declarada_dispara_revision():
    resultado = evaluar_preexistencia(poliza(), ["hernia inguinal derecha"])
    assert resultado.hay_indicios is True
    assert resultado.no_declaradas == ["hernia inguinal derecha"]


def test_sin_condiciones_detectadas_no_hay_nada_que_revisar():
    assert evaluar_preexistencia(poliza(), []).hay_indicios is False
