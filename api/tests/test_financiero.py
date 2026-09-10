"""
El desglose de dinero.

El invariante del final es el que importa: si alguna vez deja de cumplirse, hay
balboas perdidos en el calculo y alguien esta pagando de mas.
"""

from app.dominio.financiero import a_centavos, calcular_desglose
from tests.test_reglas import poliza, procedimiento


def test_el_caso_canonico_linea_por_linea():
    """
    Plan preferente: cubre el 90%, el asegurado paga 20% de coaseguro.
    Deducible de 500 sin consumir, cotizacion de 6.800.

        deducible          500,00  -> paciente
        base            6.300,00
        no reconocido     630,00  (el 10% que el plan no cubre) -> paciente
        elegible        5.670,00
        coaseguro       1.134,00  (20% de lo elegible) -> paciente
        aseguradora     4.536,00
        paciente        2.264,00
    """
    d = calcular_desglose(poliza(), procedimiento(), 6_800.0)
    assert d.deducible_aplicado == 500.0
    assert d.no_reconocido_por_plan == 630.0
    assert d.coaseguro_asegurado == 1_134.0
    assert d.cubierto_aseguradora == 4_536.0
    assert d.a_cargo_paciente == 2_264.0
    assert d.excede_tope is False


def test_un_deducible_ya_consumido_no_se_vuelve_a_cobrar():
    d = calcular_desglose(poliza(deducible_consumido=500.0), procedimiento(), 6_800.0)
    assert d.deducible_aplicado == 0.0
    assert d.cubierto_aseguradora == 4_896.0


def test_el_deducible_no_puede_pasarse_del_monto_cotizado():
    d = calcular_desglose(poliza(deducible_anual=5_000.0), procedimiento(), 800.0)
    assert d.deducible_aplicado == 800.0
    assert d.cubierto_aseguradora == 0.0
    assert d.a_cargo_paciente == 800.0


def test_el_tope_anual_es_el_techo_de_lo_que_paga_la_aseguradora():
    p = poliza(deducible_consumido=500.0, tope_anual=50_000.0, tope_consumido=46_800.0)
    d = calcular_desglose(p, procedimiento(), 32_000.0)
    assert d.tope_disponible_antes == 3_200.0
    assert d.cubierto_aseguradora == 3_200.0
    assert d.excede_tope is True
    assert d.exceso_sobre_tope > 0
    assert d.tope_disponible_despues == 0.0
    # Todo lo que el tope no cubre cae en el paciente.
    assert d.a_cargo_paciente == 28_800.0


def test_un_procedimiento_sin_cobertura_en_el_plan_lo_paga_todo_el_paciente():
    proc = procedimiento(cobertura_porcentaje={"basico": 0, "preferente": 0, "ejecutivo": 0})
    d = calcular_desglose(poliza(deducible_consumido=500.0), proc, 5_500.0)
    assert d.cubierto_aseguradora == 0.0
    assert d.a_cargo_paciente == 5_500.0


def test_el_dinero_siempre_cuadra():
    """
    paciente + aseguradora == cotizado, en todas las combinaciones.

    Se compara en CENTAVOS, no en balboas: sumar dos float exactos al centavo
    puede dar 14500.329999999998, que es un artefacto de la representacion
    binaria y no un descuadre. En enteros no hay ambiguedad.
    """
    for monto in (250.0, 800.0, 6_800.0, 14_500.33, 32_000.0, 99_999.99):
        for plan in ("basico", "preferente", "ejecutivo"):
            for consumido in (0.0, 300.0, 500.0):
                for tope_consumido in (0.0, 46_800.0, 50_000.0):
                    d = calcular_desglose(
                        poliza(
                            plan=plan,
                            deducible_consumido=consumido,
                            tope_consumido=tope_consumido,
                        ),
                        procedimiento(),
                        monto,
                    )
                    assert a_centavos(d.cubierto_aseguradora) + a_centavos(
                        d.a_cargo_paciente
                    ) == a_centavos(d.monto_cotizado), (
                        f"descuadre con monto={monto} plan={plan} "
                        f"deducible={consumido} tope={tope_consumido}"
                    )
