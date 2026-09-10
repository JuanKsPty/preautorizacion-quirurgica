"""
Los ocho escenarios sembrados, contra el motor de reglas y sin modelo.

Es la prueba mas valiosa de la suite: cada informe de demostracion esta hecho
para recorrer un camino de dictamen distinto, y esto garantiza que los ocho
siguen dando lo que deben despues de cualquier refactor. Si un dia hay que
tocar la precedencia, esta es la red.
"""

import pytest

from app.dominio.financiero import calcular_desglose
from app.dominio.reglas import construir_expediente
from app.dominio.veredicto import decidir
from app.repositorios.datos_demo import INFORMES, POLIZAS, PROCEDIMIENTOS

# (informe, cpt que el modelo debe identificar, condiciones previas que debe leer)
ESCENARIOS = [
    ("INF-2026-0031", "47562", [], "APROBADO"),
    ("INF-2026-0032", "29881", [], "RECHAZADO"),
    ("INF-2026-0033", "15877", [], "RECHAZADO"),
    ("INF-2026-0034", "63030", [], "DOCUMENTOS_FALTANTES"),
    ("INF-2026-0035", "49505", ["hernia inguinal derecha"], "REVISION_MEDICA"),
    ("INF-2026-0036", "44970", [], "APROBADO"),
    ("INF-2026-0037", "27447", [], "APROBADO_CON_CONDICIONES"),
    ("INF-2026-0038", "66984", [], "RECHAZADO"),
]

_POLIZAS = {p.numero: p for p in POLIZAS}
_INFORMES = {i.codigo: i for i in INFORMES}
_PROCS = {p.cpt: p for p in PROCEDIMIENTOS}


def test_los_ocho_escenarios_estan_sembrados():
    assert len(ESCENARIOS) == len(INFORMES) == 8
    veredictos = {v for *_, v in ESCENARIOS}
    # Los cinco veredictos posibles quedan cubiertos por la demo.
    assert veredictos == {
        "APROBADO",
        "APROBADO_CON_CONDICIONES",
        "DOCUMENTOS_FALTANTES",
        "RECHAZADO",
        "REVISION_MEDICA",
    }


@pytest.mark.parametrize(("codigo", "cpt", "condiciones", "esperado"), ESCENARIOS)
def test_cada_escenario_da_su_veredicto(codigo, cpt, condiciones, esperado):
    informe = _INFORMES[codigo]
    poliza = _POLIZAS[informe.numero_poliza]
    procedimiento = _PROCS[cpt]

    expediente = construir_expediente(poliza, procedimiento, informe, condiciones)
    desglose = (
        calcular_desglose(poliza, procedimiento, informe.monto_cotizado)
        if expediente.cobertura.cubierto
        else None
    )
    veredicto, motivos = decidir(expediente, desglose)

    assert veredicto == esperado, f"{codigo}: {motivos}"
    assert motivos, "un veredicto sin motivo no es auditable"


def test_la_urgencia_es_lo_que_salva_a_la_apendicitis():
    """
    Yaritza lleva 57 dias afiliada y su plan exige 90 para una apendicectomia.
    Electiva se rechazaria; como urgencia se aprueba. Es el escenario que
    demuestra por que la exoneracion por emergencia no es un detalle.
    """
    informe = _INFORMES["INF-2026-0036"]
    poliza = _POLIZAS[informe.numero_poliza]
    procedimiento = _PROCS["44970"]

    como_urgencia = construir_expediente(poliza, procedimiento, informe)
    assert como_urgencia.carencia.cumple is True
    assert como_urgencia.carencia.exonerada_por_emergencia is True
    assert decidir(como_urgencia, None)[0] == "APROBADO"

    electivo = construir_expediente(
        poliza, procedimiento, informe.model_copy(update={"es_emergencia": False})
    )
    assert electivo.carencia.cumple is False
    assert decidir(electivo, None)[0] == "RECHAZADO"
