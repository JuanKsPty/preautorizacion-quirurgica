"""
Reparto del costo entre aseguradora y paciente.

**Toda la aritmetica va en centavos enteros.** Con `float` el calculo sale bien
al centavo pero el invariante deja de comprobarse: 8960.21 + 5540.12 da
14500.329999999998 y no 14500.33, porque ninguno de los tres es representable en
binario. En centavos no hay nada que redondear y el cuadre es exacto.

El orden de aplicacion no es arbitrario, es el de una poliza de gastos medicos
mayores: primero el deducible, despues el porcentaje que el plan reconoce del
procedimiento, despues el coaseguro sobre lo reconocido, y al final el tope
anual como techo de lo que paga la aseguradora.

Invariante que prueba tests/test_financiero.py, en centavos:

    a_cargo_paciente + cubierto_aseguradora == monto_cotizado
"""

from app.dominio.esquemas import Desglose, Poliza, Procedimiento


def a_centavos(valor: float) -> int:
    return int(round(valor * 100))


def a_balboas(centavos: int) -> float:
    return centavos / 100


def _reparto(centavos: int, porcentaje: int) -> int:
    """Porcentaje de una cantidad en centavos, redondeando al centavo mas cercano."""
    return int(round(centavos * porcentaje / 100))


def calcular_desglose(
    poliza: Poliza, procedimiento: Procedimiento, monto_cotizado: float
) -> Desglose:
    cobertura_pct = procedimiento.cobertura_para(poliza.plan)

    cotizado = a_centavos(monto_cotizado)

    # 1. Deducible anual pendiente: lo primero que sale del bolsillo del paciente.
    deducible = min(a_centavos(poliza.deducible_pendiente), cotizado)
    base = cotizado - deducible

    # 2. De lo que queda, el plan solo reconoce su porcentaje de cobertura.
    elegible = _reparto(base, cobertura_pct)
    no_reconocido = base - elegible

    # 3. Sobre el gasto reconocido, el asegurado paga su coaseguro.
    coaseguro = _reparto(elegible, poliza.coaseguro_porcentaje)
    cubierto_bruto = elegible - coaseguro

    # 4. El tope anual es el techo de lo que la aseguradora puede pagar.
    tope_antes = a_centavos(poliza.tope_disponible)
    cubierto = min(cubierto_bruto, tope_antes)
    exceso_tope = cubierto_bruto - cubierto

    # Se despeja por diferencia: garantiza el cuadre sin depender de como
    # cayeron los redondeos de cada tramo.
    paciente = cotizado - cubierto

    return Desglose(
        monto_cotizado=a_balboas(cotizado),
        cobertura_porcentaje=cobertura_pct,
        deducible_aplicado=a_balboas(deducible),
        coaseguro_asegurado=a_balboas(coaseguro),
        no_reconocido_por_plan=a_balboas(no_reconocido),
        exceso_sobre_tope=a_balboas(exceso_tope),
        cubierto_aseguradora=a_balboas(cubierto),
        a_cargo_paciente=a_balboas(paciente),
        tope_disponible_antes=a_balboas(tope_antes),
        tope_disponible_despues=a_balboas(tope_antes - cubierto),
        excede_tope=exceso_tope > 0,
    )
