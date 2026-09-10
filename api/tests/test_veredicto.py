"""
La precedencia entre reglas.

Cuando fallan varias a la vez, el motivo que se le cita al asegurado tiene que
ser siempre el mismo. Esto lo fija.
"""

from datetime import date

from app.dominio.esquemas import InformeMedico
from app.dominio.financiero import calcular_desglose
from app.dominio.reglas import construir_expediente
from app.dominio.veredicto import construir_chequeos, decidir
from tests.test_reglas import poliza, procedimiento


def informe(**cambios) -> InformeMedico:
    base = {
        "codigo": "INF-TEST-0001",
        "paciente": "Persona de Prueba",
        "cedula": "8-000-0000",
        "numero_poliza": "POL-TEST-0001",
        "hospital": "Hospital de Prueba",
        "medico_tratante": "Dra. Prueba",
        "especialidad": "Cirugía general",
        "fecha_informe": date(2026, 6, 1),
        "fecha_cirugia_propuesta": date(2026, 6, 15),
        "monto_cotizado": 6_800.0,
        "documentos_adjuntos": ["Informe médico firmado", "Copia de cédula"],
        "texto": "Relato clínico de prueba.",
    }
    return InformeMedico(**(base | cambios))


def resolver(p, proc, inf, condiciones=None):
    exp = construir_expediente(p, proc, inf, condiciones or [])
    des = calcular_desglose(p, proc, inf.monto_cotizado) if exp.cobertura.cubierto else None
    return decidir(exp, des)[0]


def test_todo_conforme_aprueba():
    assert resolver(poliza(), procedimiento(), informe()) == "APROBADO"


def test_la_poliza_en_mora_gana_a_todo_lo_demas():
    """
    Aunque falten documentos Y no se cumpla la carencia, el motivo citado es la
    mora: es la condicion que hace irrelevante todo el resto del expediente.
    """
    veredicto = resolver(
        poliza(estado="en_mora", inicio_vigencia=date(2026, 6, 1)),
        procedimiento(),
        informe(documentos_adjuntos=[]),
    )
    assert veredicto == "RECHAZADO"


def test_una_exclusion_gana_a_los_documentos_faltantes():
    """
    Pedir papeles para una cirugia que esta excluida manda al paciente a una
    diligencia inutil. La exclusion se cita primero.
    """
    veredicto = resolver(
        poliza(),
        procedimiento(exclusion="cirugía con fines estéticos"),
        informe(documentos_adjuntos=[]),
    )
    assert veredicto == "RECHAZADO"


def test_la_carencia_gana_a_los_documentos_faltantes():
    veredicto = resolver(
        poliza(inicio_vigencia=date(2026, 6, 1)),
        procedimiento(),
        informe(documentos_adjuntos=[]),
    )
    assert veredicto == "RECHAZADO"


def test_una_preexistencia_no_declarada_gana_a_los_documentos_faltantes():
    """
    Igual que la exclusion: si el caso va a revision medica de todos modos, no
    se le pide antes al paciente que corra por unos papeles.
    """
    veredicto = resolver(
        poliza(),
        procedimiento(),
        informe(documentos_adjuntos=[]),
        condiciones=["hernia inguinal de 4 años"],
    )
    assert veredicto == "REVISION_MEDICA"


def test_faltar_documentos_no_rechaza_pide():
    veredicto = resolver(poliza(), procedimiento(), informe(documentos_adjuntos=[]))
    assert veredicto == "DOCUMENTOS_FALTANTES"


def test_el_tope_insuficiente_aprueba_con_condiciones_no_rechaza():
    """Que la suma asegurada no alcance no es un rechazo: es una salvedad."""
    veredicto = resolver(
        poliza(deducible_consumido=500.0, tope_consumido=46_800.0),
        procedimiento(),
        informe(monto_cotizado=32_000.0),
    )
    assert veredicto == "APROBADO_CON_CONDICIONES"


def test_siempre_se_reportan_los_seis_chequeos():
    """La UI pinta la lista completa, incluidos los que no aplican."""
    exp = construir_expediente(poliza(), procedimiento(), informe())
    des = calcular_desglose(poliza(), procedimiento(), 6_800.0)
    chequeos = construir_chequeos(exp, des)
    assert len(chequeos) == 6
    assert [c.nombre for c in chequeos] == [
        "Vigencia de la poliza",
        "Cobertura del procedimiento",
        "Periodo de carencia",
        "Preexistencias",
        "Expediente documental",
        "Suma asegurada",
    ]
