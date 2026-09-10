"""
Las herramientas del agente y, sobre todo, sus dos validaciones.

`emitir_dictamen` es la puerta por la que el modelo tendria que pasar para
alucinar: cambiando el veredicto o escribiendo una cifra que no existe. Estas
pruebas cierran las dos, y son lo que convierte "el agente no inventa numeros"
en una garantia comprobable en vez de una instruccion del prompt.
"""

import asyncio

import pytest

from app.agente.herramientas import (
    ErrorHerramienta,
    EstadoEjecucion,
    ejecutar_herramienta,
    emparejar_por_texto,
)
from app.repositorios.datos_demo import INFORMES, POLIZAS, PROCEDIMIENTOS

_POLIZAS = {p.numero: p for p in POLIZAS}
_INFORMES = {i.codigo: i for i in INFORMES}


def estado_de(codigo_informe: str) -> EstadoEjecucion:
    informe = _INFORMES[codigo_informe]
    return EstadoEjecucion(
        folio="PA-" + codigo_informe.removeprefix("INF-"),
        poliza=_POLIZAS[informe.numero_poliza],
        informe=informe,
        catalogo=list(PROCEDIMIENTOS),
    )


def correr(nombre: str, argumentos: dict, estado: EstadoEjecucion) -> dict:
    return asyncio.run(ejecutar_herramienta(nombre, argumentos, estado))


ANALISIS_VALIDO = {
    "diagnostico_principal": "Colelitiasis con colecistitis crónica",
    "cie10": "K80.1",
    "procedimiento_descrito": "extirpación de la vesícula biliar por laparoscopía",
    "lateralidad": "no_aplica",
    "urgencia": "electiva",
    "condiciones_previas_detectadas": [],
    "informe_sustenta_procedimiento": True,
    "observaciones": "",
}


def hasta_evaluar(codigo: str = "INF-2026-0031") -> EstadoEjecucion:
    """Deja el estado justo antes de emitir el dictamen."""
    estado = estado_de(codigo)
    correr("consultar_poliza", {}, estado)
    correr("consultar_informe", {}, estado)
    correr("registrar_analisis_clinico", ANALISIS_VALIDO, estado)
    correr("seleccionar_procedimiento", {"cpt": "47562", "justificacion": "x"}, estado)
    correr("evaluar_expediente", {}, estado)
    return estado


# ------------------------------------------------------------------- consultas


def test_la_poliza_llega_con_las_cifras_ya_formateadas():
    estado = estado_de("INF-2026-0031")
    salida = correr("consultar_poliza", {}, estado)
    assert salida["plan"] == "Preferente"
    assert salida["tope_disponible"].startswith("B/. ")
    # Consultar la poliza autoriza sus cifras para los textos del dictamen.
    assert estado.cifras_permitidas


def test_el_informe_incluye_el_relato_clinico_completo():
    salida = correr("consultar_informe", {}, estado_de("INF-2026-0031"))
    assert "Ultrasonido abdominal" in salida["relato_clinico"]
    assert salida["declarado_como_emergencia"] is False


# --------------------------------------------------------------- procedimiento


def test_buscar_procedimiento_mapea_la_prosa_del_medico_al_cpt():
    salida = correr(
        "buscar_procedimiento",
        {"descripcion": "cirugía de vesícula"},
        estado_de("INF-2026-0031"),
    )
    assert salida["candidatos"][0]["cpt"] == "47562"


def test_una_descripcion_sin_sentido_no_devuelve_candidatos():
    with pytest.raises(ErrorHerramienta, match="Ningún procedimiento"):
        correr(
            "buscar_procedimiento",
            {"descripcion": "zzzzz qqqqq wwwww"},
            estado_de("INF-2026-0031"),
        )


def test_no_se_puede_seleccionar_un_cpt_fuera_del_catalogo():
    with pytest.raises(ErrorHerramienta, match="no está en el catálogo"):
        correr(
            "seleccionar_procedimiento",
            {"cpt": "00000", "justificacion": "inventado"},
            estado_de("INF-2026-0031"),
        )


# ----------------------------------------------------------- analisis clinico


def test_un_cie10_con_forma_invalida_se_rechaza():
    estado = estado_de("INF-2026-0031")
    with pytest.raises(ErrorHerramienta, match="CIE-10"):
        correr(
            "registrar_analisis_clinico",
            ANALISIS_VALIDO | {"cie10": "colelitiasis"},
            estado,
        )


# ------------------------------------------------------------------ evaluacion


def test_no_se_puede_evaluar_sin_haber_analizado_ni_elegido_procedimiento():
    with pytest.raises(ErrorHerramienta, match="Antes de evaluar"):
        correr("evaluar_expediente", {}, estado_de("INF-2026-0031"))


def test_la_evaluacion_devuelve_veredicto_chequeos_y_desglose():
    estado = hasta_evaluar()
    assert estado.veredicto == "APROBADO"
    assert len(estado.chequeos) == 6
    assert estado.desglose is not None


def test_si_el_informe_no_sustenta_el_procedimiento_el_caso_va_a_revision():
    """
    El juicio del modelo solo puede BAJAR en la escala. Un agente automatico no
    niega una cirugia: la manda a un auditor humano.
    """
    estado = estado_de("INF-2026-0031")
    correr(
        "registrar_analisis_clinico",
        ANALISIS_VALIDO | {"informe_sustenta_procedimiento": False},
        estado,
    )
    correr("seleccionar_procedimiento", {"cpt": "47562", "justificacion": "x"}, estado)
    salida = correr("evaluar_expediente", {}, estado)
    assert salida["veredicto"] == "REVISION_MEDICA"


# -------------------------------------------------- las dos validaciones clave


def test_el_modelo_no_puede_cambiar_el_veredicto():
    estado = hasta_evaluar()
    with pytest.raises(ErrorHerramienta, match="El veredicto correcto es «APROBADO»"):
        correr(
            "emitir_dictamen",
            {
                "veredicto": "RECHAZADO",
                "resumen": "x",
                "carta_paciente": "x",
                "justificacion_tecnica": "x",
            },
            estado,
        )


def test_el_modelo_no_puede_inventar_una_cifra_en_la_carta():
    estado = hasta_evaluar()
    with pytest.raises(ErrorHerramienta, match="no salieron de ninguna herramienta"):
        correr(
            "emitir_dictamen",
            {
                "veredicto": "APROBADO",
                "resumen": "Aprobado",
                # 9.999,99 no aparece en ningun resultado de herramienta.
                "carta_paciente": "La aseguradora cubrirá B/. 9,999.99 de su cirugía.",
                "justificacion_tecnica": "x",
            },
            estado,
        )


def test_una_carta_que_usa_las_cifras_reales_se_acepta():
    estado = hasta_evaluar()
    assert estado.desglose is not None
    cubierto = estado.desglose.cubierto_aseguradora
    salida = correr(
        "emitir_dictamen",
        {
            "veredicto": "APROBADO",
            "resumen": "Su cirugía fue aprobada.",
            "carta_paciente": f"La aseguradora cubrirá B/. {cubierto:,.2f} del procedimiento.",
            "justificacion_tecnica": "CPT 47562, CIE-10 K80.1, carencia cumplida.",
        },
        estado,
    )
    assert salida["emitido"] is True
    assert estado.dictamen is not None
    assert estado.dictamen.veredicto == "APROBADO"
    assert estado.dictamen.cpt_identificado == "47562"


def test_no_se_puede_emitir_sin_haber_evaluado():
    with pytest.raises(ErrorHerramienta, match="Todavía no se ha evaluado"):
        correr(
            "emitir_dictamen",
            {
                "veredicto": "APROBADO",
                "resumen": "x",
                "carta_paciente": "x",
                "justificacion_tecnica": "x",
            },
            estado_de("INF-2026-0031"),
        )


def test_una_herramienta_inexistente_da_error_de_herramienta_no_excepcion():
    with pytest.raises(ErrorHerramienta, match="No existe la herramienta"):
        correr("herramienta_inventada", {}, estado_de("INF-2026-0031"))


# --------------------------------------------- emparejador sin modelo (respaldo)


def test_el_emparejador_sin_modelo_acierta_en_los_ocho_informes():
    """
    El camino sin IA tiene que identificar el procedimiento leyendo el informe.
    Es mas basto que el mapeo del modelo, pero debe acertar en la demo.
    """
    esperado = {
        "INF-2026-0031": "47562",
        "INF-2026-0032": "29881",
        "INF-2026-0033": "15877",
        "INF-2026-0034": "63030",
        "INF-2026-0035": "49505",
        "INF-2026-0036": "44970",
        "INF-2026-0037": "27447",
        "INF-2026-0038": "66984",
    }
    for codigo, cpt in esperado.items():
        emparejado = emparejar_por_texto(list(PROCEDIMIENTOS), _INFORMES[codigo].texto)
        assert emparejado is not None, f"{codigo}: sin candidato"
        assert emparejado[0].cpt == cpt, f"{codigo}: dio {emparejado[0].nombre}"
