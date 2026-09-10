"""
Las herramientas del agente y su despachador.

El expediente completo (poliza, informe, catalogo) se lee UNA VEZ antes de
arrancar el bucle y vive en `EstadoEjecucion`. Las herramientas son funciones
puras sobre ese snapshot: cero red dentro del bucle. Eso hace que cada llamada
tarde microsegundos en vez de un viaje a Notion, que el resultado sea
reproducible, que se pueda probar sin mocks de HTTP y, sobre todo, que un limite
de peticiones de Notion no pueda reventar la evaluacion a mitad de una demo.

Dos validaciones en `emitir_dictamen` son las que convierten "el modelo no
inventa numeros" en una garantia y no en una instruccion del prompt:

  * el veredicto que escribe el modelo tiene que ser identico al que calculo
    `evaluar_expediente`;
  * toda cifra en balboas de la carta tiene que haber salido de una herramienta.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.dominio.esquemas import (
    NOMBRE_PLAN,
    Chequeo,
    Desglose,
    Dictamen,
    InformeMedico,
    Poliza,
    Procedimiento,
    Veredicto,
)
from app.dominio.financiero import calcular_desglose
from app.dominio.reglas import Expediente, construir_expediente
from app.dominio.veredicto import construir_chequeos, decidir

# CIE-10: una letra (salvo U), dos digitos y un subcodigo opcional.
PATRON_CIE10 = re.compile(r"^[A-TV-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$")
# Cifras en balboas dentro de un texto: "B/. 6,800.00", "B/.6800".
PATRON_DINERO = re.compile(r"B/\.\s*([\d.,]+)")


class ErrorHerramienta(Exception):
    """Vuelve al modelo como tool_result con is_error, no rompe el stream."""


def dinero(valor: float) -> str:
    return f"B/. {valor:,.2f}"


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip()


def _cifras_en(texto: str) -> set[float]:
    """Las cantidades en balboas que aparecen escritas en un texto."""
    encontradas: set[float] = set()
    for crudo in PATRON_DINERO.findall(texto):
        limpio = crudo.rstrip(".,").replace(",", "")
        try:
            encontradas.add(round(float(limpio), 2))
        except ValueError:
            continue
    return encontradas


class AnalisisClinico(BaseModel):
    """Lo que el modelo extrae del informe en texto libre."""

    diagnostico_principal: str
    cie10: str
    procedimiento_descrito: str
    lateralidad: Literal["izquierda", "derecha", "bilateral", "no_aplica"]
    urgencia: Literal["electiva", "urgente", "emergencia"]
    condiciones_previas_detectadas: list[str] = Field(default_factory=list)
    informe_sustenta_procedimiento: bool
    observaciones: str = ""


@dataclass
class EstadoEjecucion:
    """Snapshot del caso mas lo que el bucle va acumulando."""

    folio: str
    poliza: Poliza
    informe: InformeMedico
    catalogo: list[Procedimiento]
    analisis: AnalisisClinico | None = None
    procedimiento: Procedimiento | None = None
    expediente: Expediente | None = None
    desglose: Desglose | None = None
    veredicto: Veredicto | None = None
    motivos: list[str] = field(default_factory=list)
    chequeos: list[Chequeo] = field(default_factory=list)
    # Toda cantidad en balboas que alguna herramienta ha devuelto.
    cifras_permitidas: set[float] = field(default_factory=set)
    dictamen: Dictamen | None = None

    def permitir(self, *valores: float) -> None:
        for valor in valores:
            self.cifras_permitidas.add(round(valor, 2))


# --------------------------------------------------------------- definiciones

HERRAMIENTAS: list[dict[str, Any]] = [
    {
        "name": "consultar_poliza",
        "description": (
            "Devuelve los términos de la póliza del asegurado: plan, estado, vigencia, "
            "deducible, coaseguro, tope anual y preexistencias declaradas. Es la única "
            "fuente válida de estas cifras."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "consultar_informe",
        "description": (
            "Devuelve el informe médico que envió el hospital, incluido el relato "
            "clínico completo en texto libre y la lista de documentos adjuntos."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "buscar_procedimiento",
        "description": (
            "Busca en el catálogo de procedimientos a partir de cómo lo describe el "
            "informe. Devuelve los candidatos con su código CPT, la carencia que exige "
            "el plan del asegurado y su porcentaje de cobertura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "descripcion": {
                    "type": "string",
                    "description": (
                        "El procedimiento tal como lo describe el informe médico, "
                        "con las palabras del médico."
                    ),
                }
            },
            "required": ["descripcion"],
            "additionalProperties": False,
        },
    },
    {
        "name": "registrar_analisis_clinico",
        "description": (
            "Registra lo que extrajiste del informe en texto libre. Las condiciones "
            "previas que anotes se comparan contra las preexistencias declaradas en la "
            "póliza, así que incluye cualquier padecimiento que el relato sitúe antes "
            "del inicio de la cobertura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "diagnostico_principal": {"type": "string"},
                "cie10": {
                    "type": "string",
                    "description": "Código CIE-10, por ejemplo K80.1 o M51.1.",
                },
                "procedimiento_descrito": {"type": "string"},
                "lateralidad": {
                    "type": "string",
                    "enum": ["izquierda", "derecha", "bilateral", "no_aplica"],
                },
                "urgencia": {
                    "type": "string",
                    "enum": ["electiva", "urgente", "emergencia"],
                },
                "condiciones_previas_detectadas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Padecimientos que el relato sugiere anteriores a la póliza. "
                        "Lista vacía si el informe no menciona ninguno."
                    ),
                },
                "informe_sustenta_procedimiento": {
                    "type": "boolean",
                    "description": (
                        "true si los hallazgos clínicos y los estudios justifican el "
                        "procedimiento propuesto."
                    ),
                },
                "observaciones": {"type": "string"},
            },
            "required": [
                "diagnostico_principal",
                "cie10",
                "procedimiento_descrito",
                "lateralidad",
                "urgencia",
                "condiciones_previas_detectadas",
                "informe_sustenta_procedimiento",
                "observaciones",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "seleccionar_procedimiento",
        "description": (
            "Fija el código CPT del caso. Debe ser uno de los que devolvió buscar_procedimiento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cpt": {"type": "string"},
                "justificacion": {
                    "type": "string",
                    "description": "Por qué ese código corresponde a lo que describe el informe.",
                },
            },
            "required": ["cpt", "justificacion"],
            "additionalProperties": False,
        },
    },
    {
        "name": "evaluar_expediente",
        "description": (
            "Aplica las condiciones de la póliza: vigencia, carencia, cobertura, "
            "preexistencias, documentos y desglose de dinero. DETERMINA EL VEREDICTO. "
            "Requiere haber llamado antes a registrar_analisis_clinico y "
            "seleccionar_procedimiento."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "emitir_dictamen",
        "description": (
            "Cierra el caso. El veredicto debe ser exactamente el que devolvió "
            "evaluar_expediente, y toda cifra en balboas que escribas debe haber salido "
            "de una herramienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "veredicto": {
                    "type": "string",
                    "enum": [
                        "APROBADO",
                        "APROBADO_CON_CONDICIONES",
                        "DOCUMENTOS_FALTANTES",
                        "RECHAZADO",
                        "REVISION_MEDICA",
                    ],
                },
                "resumen": {
                    "type": "string",
                    "description": "Una frase con la resolución y su motivo principal.",
                },
                "carta_paciente": {
                    "type": "string",
                    "description": (
                        "Para el asegurado: segunda persona, español llano, sin códigos "
                        "ni jerga. Entre 4 y 8 frases."
                    ),
                },
                "justificacion_tecnica": {
                    "type": "string",
                    "description": (
                        "Para el auditor: CIE-10, CPT, días de carencia contra los "
                        "exigidos, porcentajes y la regla que sostiene el veredicto."
                    ),
                },
            },
            "required": [
                "veredicto",
                "resumen",
                "carta_paciente",
                "justificacion_tecnica",
            ],
            "additionalProperties": False,
        },
    },
]

NOMBRES_HERRAMIENTAS = [h["name"] for h in HERRAMIENTAS]


# ----------------------------------------------------------------- ejecutores


def _ficha_procedimiento(proc: Procedimiento, plan: str) -> dict[str, Any]:
    return {
        "cpt": proc.cpt,
        "nombre": proc.nombre,
        "categoria": proc.categoria,
        "carencia_exigida_dias": proc.carencia_para(plan),  # type: ignore[arg-type]
        "cobertura_en_este_plan": f"{proc.cobertura_para(plan)}%",  # type: ignore[arg-type]
        "documentos_requeridos": proc.documentos_requeridos,
        "exclusion": proc.exclusion,
    }


def _puntuar(descripcion: str, proc: Procedimiento) -> float:
    """Parecido entre la prosa del medico y las formas conocidas del procedimiento."""
    from difflib import SequenceMatcher

    objetivo = _normalizar(descripcion)
    mejor = 0.0
    for variante in [proc.nombre, *proc.sinonimos, proc.cpt]:
        candidato = _normalizar(variante)
        if not candidato:
            continue
        if candidato in objetivo or objetivo in candidato:
            mejor = max(mejor, 0.95)
            continue
        mejor = max(mejor, SequenceMatcher(None, objetivo, candidato).ratio())
    return round(mejor, 3)


def _consultar_poliza(estado: EstadoEjecucion) -> dict[str, Any]:
    p = estado.poliza
    estado.permitir(p.deducible_anual, p.deducible_pendiente, p.tope_anual, p.tope_disponible)
    return {
        "numero": p.numero,
        "titular": p.titular,
        "cedula": p.cedula,
        "plan": NOMBRE_PLAN[p.plan],
        "estado": p.estado,
        "inicio_vigencia": p.inicio_vigencia.isoformat(),
        "fin_vigencia": p.fin_vigencia.isoformat(),
        "deducible_anual": dinero(p.deducible_anual),
        "deducible_pendiente": dinero(p.deducible_pendiente),
        "coaseguro_del_asegurado": f"{p.coaseguro_porcentaje}%",
        "tope_anual": dinero(p.tope_anual),
        "tope_disponible": dinero(p.tope_disponible),
        "red_preferente": p.red_preferente,
        "preexistencias_declaradas": p.preexistencias_declaradas,
    }


def _consultar_informe(estado: EstadoEjecucion) -> dict[str, Any]:
    i = estado.informe
    estado.permitir(i.monto_cotizado)
    return {
        "codigo": i.codigo,
        "paciente": i.paciente,
        "cedula": i.cedula,
        "numero_poliza": i.numero_poliza,
        "hospital": i.hospital,
        "medico_tratante": i.medico_tratante,
        "especialidad": i.especialidad,
        "fecha_informe": i.fecha_informe.isoformat(),
        "fecha_cirugia_propuesta": i.fecha_cirugia_propuesta.isoformat(),
        "declarado_como_emergencia": i.es_emergencia,
        "monto_cotizado": dinero(i.monto_cotizado),
        "documentos_adjuntos": i.documentos_adjuntos,
        "relato_clinico": i.texto,
    }


def _buscar_procedimiento(estado: EstadoEjecucion, argumentos: dict[str, Any]) -> dict[str, Any]:
    descripcion = str(argumentos.get("descripcion", "")).strip()
    if not descripcion:
        raise ErrorHerramienta(
            "Falta `descripcion`: pásame el procedimiento como lo escribe el informe."
        )

    puntuados = sorted(
        ((_puntuar(descripcion, p), p) for p in estado.catalogo),
        key=lambda par: par[0],
        reverse=True,
    )
    candidatos = [
        {"puntaje": puntaje, **_ficha_procedimiento(proc, estado.poliza.plan)}
        for puntaje, proc in puntuados[:5]
        if puntaje >= 0.35
    ]
    if not candidatos:
        raise ErrorHerramienta(
            f"Ningún procedimiento del catálogo se parece a «{descripcion}». "
            "Prueba con el nombre técnico del procedimiento, no con el diagnóstico."
        )
    return {"consulta": descripcion, "candidatos": candidatos}


def _registrar_analisis(estado: EstadoEjecucion, argumentos: dict[str, Any]) -> dict[str, Any]:
    try:
        analisis = AnalisisClinico.model_validate(argumentos)
    except ValidationError as error:
        raise ErrorHerramienta(f"El análisis clínico no valida: {error.errors()}") from error

    if not PATRON_CIE10.match(analisis.cie10.strip().upper()):
        raise ErrorHerramienta(
            f"«{analisis.cie10}» no tiene forma de código CIE-10. "
            "Se espera una letra, dos dígitos y un subcódigo opcional: K80.1, M51.1, S83.2."
        )

    analisis.cie10 = analisis.cie10.strip().upper()
    estado.analisis = analisis
    advertencias: list[str] = []
    if not analisis.informe_sustenta_procedimiento:
        advertencias.append(
            "Marcaste que el informe no sustenta el procedimiento: el caso irá a revisión médica."
        )
    if analisis.condiciones_previas_detectadas:
        advertencias.append(
            "Las condiciones previas se compararán contra las preexistencias declaradas."
        )
    return {"registrado": True, "cie10": analisis.cie10, "advertencias": advertencias}


def _seleccionar_procedimiento(
    estado: EstadoEjecucion, argumentos: dict[str, Any]
) -> dict[str, Any]:
    cpt = str(argumentos.get("cpt", "")).strip()
    procedimiento = next((p for p in estado.catalogo if p.cpt == cpt), None)
    if procedimiento is None:
        disponibles = ", ".join(p.cpt for p in estado.catalogo)
        raise ErrorHerramienta(
            f"El CPT {cpt!r} no está en el catálogo. Códigos disponibles: {disponibles}."
        )
    estado.procedimiento = procedimiento
    return {
        "seleccionado": True,
        **_ficha_procedimiento(procedimiento, estado.poliza.plan),
        "plan_del_asegurado": NOMBRE_PLAN[estado.poliza.plan],
    }


def _evaluar_expediente(estado: EstadoEjecucion) -> dict[str, Any]:
    pendientes = [
        nombre
        for nombre, listo in (
            ("registrar_analisis_clinico", estado.analisis is not None),
            ("seleccionar_procedimiento", estado.procedimiento is not None),
        )
        if not listo
    ]
    if pendientes:
        raise ErrorHerramienta(
            "Antes de evaluar hace falta llamar a: " + ", ".join(pendientes) + "."
        )

    assert estado.analisis is not None and estado.procedimiento is not None

    expediente = construir_expediente(
        estado.poliza,
        estado.procedimiento,
        estado.informe,
        estado.analisis.condiciones_previas_detectadas,
    )
    # El desglose solo tiene sentido si el procedimiento esta cubierto.
    desglose: Desglose | None = None
    if expediente.cobertura.cubierto:
        desglose = calcular_desglose(
            estado.poliza, estado.procedimiento, estado.informe.monto_cotizado
        )
        estado.permitir(
            desglose.monto_cotizado,
            desglose.deducible_aplicado,
            desglose.coaseguro_asegurado,
            desglose.no_reconocido_por_plan,
            desglose.exceso_sobre_tope,
            desglose.cubierto_aseguradora,
            desglose.a_cargo_paciente,
            desglose.tope_disponible_antes,
            desglose.tope_disponible_despues,
        )

    veredicto, motivos = decidir(expediente, desglose)

    # El juicio clinico del modelo solo puede BAJAR en la escala, nunca subir:
    # un agente automatico no niega una cirugia, la manda a un humano.
    if not estado.analisis.informe_sustenta_procedimiento and veredicto in {
        "APROBADO",
        "APROBADO_CON_CONDICIONES",
    }:
        veredicto = "REVISION_MEDICA"
        motivos = [
            "El informe médico no sustenta clínicamente el procedimiento propuesto.",
            *motivos,
        ]

    estado.expediente = expediente
    estado.desglose = desglose
    estado.veredicto = veredicto
    estado.motivos = motivos
    estado.chequeos = construir_chequeos(expediente, desglose)

    return {
        "veredicto": veredicto,
        "motivos": motivos,
        "chequeos": [c.model_dump() for c in estado.chequeos],
        "vigencia": expediente.vigencia.model_dump(mode="json"),
        "carencia": expediente.carencia.model_dump(mode="json"),
        "cobertura": expediente.cobertura.model_dump(mode="json"),
        "documentos": expediente.documentos.model_dump(mode="json"),
        "preexistencias": expediente.preexistencia.model_dump(mode="json"),
        "desglose": (
            {
                "monto_cotizado": dinero(desglose.monto_cotizado),
                "cobertura_del_plan": f"{desglose.cobertura_porcentaje}%",
                "deducible_aplicado": dinero(desglose.deducible_aplicado),
                "no_reconocido_por_el_plan": dinero(desglose.no_reconocido_por_plan),
                "coaseguro_del_asegurado": dinero(desglose.coaseguro_asegurado),
                "exceso_sobre_el_tope": dinero(desglose.exceso_sobre_tope),
                "cubre_la_aseguradora": dinero(desglose.cubierto_aseguradora),
                "a_cargo_del_paciente": dinero(desglose.a_cargo_paciente),
                "tope_disponible_despues": dinero(desglose.tope_disponible_despues),
            }
            if desglose is not None
            else None
        ),
        "instruccion": (
            f"Llama ahora a emitir_dictamen con veredicto exactamente «{veredicto}». "
            "Copia las cifras de este resultado; no las recalcules."
        ),
    }


def _emitir_dictamen(estado: EstadoEjecucion, argumentos: dict[str, Any]) -> dict[str, Any]:
    if estado.veredicto is None:
        raise ErrorHerramienta(
            "Todavía no se ha evaluado el expediente. Llama primero a evaluar_expediente."
        )

    propuesto = str(argumentos.get("veredicto", "")).strip()
    if propuesto != estado.veredicto:
        raise ErrorHerramienta(
            f"El veredicto correcto es «{estado.veredicto}», calculado por las condiciones "
            f"de la póliza, y escribiste «{propuesto}». No lo cambies: ajusta la redacción "
            "y vuelve a emitir con el veredicto correcto."
        )

    carta = str(argumentos.get("carta_paciente", ""))
    justificacion = str(argumentos.get("justificacion_tecnica", ""))

    inventadas = sorted(_cifras_en(carta + "\n" + justificacion) - estado.cifras_permitidas)
    if inventadas:
        permitidas = ", ".join(dinero(v) for v in sorted(estado.cifras_permitidas))
        raise ErrorHerramienta(
            "Estas cantidades no salieron de ninguna herramienta: "
            + ", ".join(dinero(v) for v in inventadas)
            + f". Las cifras válidas son: {permitidas}. Reescribe los textos usándolas."
        )

    estado.dictamen = Dictamen(
        folio=estado.folio,
        veredicto=estado.veredicto,
        resumen=str(argumentos.get("resumen", "")).strip(),
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
        carta_paciente=carta.strip(),
        justificacion_tecnica=justificacion.strip(),
    )
    return {"emitido": True, "folio": estado.folio, "veredicto": estado.veredicto}


async def ejecutar_herramienta(
    nombre: str, argumentos: dict[str, Any], estado: EstadoEjecucion
) -> dict[str, Any]:
    """Despacha una herramienta. Todo es sincrono: no hay red dentro del bucle."""
    if nombre == "consultar_poliza":
        return _consultar_poliza(estado)
    if nombre == "consultar_informe":
        return _consultar_informe(estado)
    if nombre == "buscar_procedimiento":
        return _buscar_procedimiento(estado, argumentos)
    if nombre == "registrar_analisis_clinico":
        return _registrar_analisis(estado, argumentos)
    if nombre == "seleccionar_procedimiento":
        return _seleccionar_procedimiento(estado, argumentos)
    if nombre == "evaluar_expediente":
        return _evaluar_expediente(estado)
    if nombre == "emitir_dictamen":
        return _emitir_dictamen(estado, argumentos)
    raise ErrorHerramienta(
        f"No existe la herramienta {nombre!r}. Disponibles: {', '.join(NOMBRES_HERRAMIENTAS)}."
    )


def emparejar_por_texto(
    catalogo: list[Procedimiento], texto_informe: str
) -> tuple[Procedimiento, float] | None:
    """
    Empareja un informe completo con un procedimiento del catalogo sin modelo.

    No usa parecido de cadenas: contra un texto de mil palabras el parecido
    global es siempre bajo. Mide COBERTURA: que fraccion de las palabras
    significativas del nombre (o de un sinonimo) aparecen en el informe. Con
    "extirpación de la vesícula biliar por vía laparoscópica" en el relato, el
    sinonimo "cirugía de vesícula" cubre 2 de 3 palabras y gana.

    Es el respaldo de `/preautorizaciones/reglas`, que tiene que dar un veredicto
    aunque no haya clave de IA. El mapeo fino sigue siendo trabajo del modelo.
    """
    palabras_informe = set(_normalizar(texto_informe).split())
    mejor: tuple[Procedimiento, float] | None = None

    for procedimiento in catalogo:
        for variante in [procedimiento.nombre, *procedimiento.sinonimos]:
            fichas = [p for p in _normalizar(variante).split() if len(p) > 3]
            if not fichas:
                continue
            cobertura = sum(f in palabras_informe for f in fichas) / len(fichas)
            if mejor is None or cobertura > mejor[1]:
                mejor = (procedimiento, round(cobertura, 3))

    return mejor if mejor and mejor[1] >= 0.5 else None
