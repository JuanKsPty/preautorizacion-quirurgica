"""
Reglas deterministas de la pre-autorizacion.

Todo lo que es aritmetica o comparacion vive aqui, en Python, y se expone al
modelo como herramientas. El modelo orquesta y redacta; no calcula. Un dictamen
de seguros tiene que poder defenderse ante un auditor, y "lo dijo el modelo" no
es una defensa: cada numero de este modulo es reproducible y esta probado.
"""

import unicodedata
from datetime import date, timedelta

from pydantic import BaseModel

from app.dominio.esquemas import NOMBRE_PLAN, InformeMedico, Poliza, Procedimiento

MOTIVO_ESTADO: dict[str, str] = {
    "en_mora": "La poliza registra primas pendientes de pago.",
    "vencida": "La poliza no fue renovada y su vigencia expiro.",
    "cancelada": "La poliza fue cancelada.",
}


def normalizar(texto: str) -> str:
    """
    Minusculas y sin tildes, para comparar textos escritos a mano.

    Es publica porque el alta de informes la necesita para ajustar los nombres
    de documento a su grafia canonica ANTES de guardarlos: si se guarda
    «Estudio de imagenes» sin tilde, `evaluar_documentos` no lo reconoce y el
    veredicto cambia a DOCUMENTOS_FALTANTES sin ningun error a la vista.
    """
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip()


class ResultadoVigencia(BaseModel):
    vigente: bool
    estado: str
    detalle: str


def evaluar_vigencia(poliza: Poliza, fecha: date) -> ResultadoVigencia:
    """La poliza tiene que estar viva y al dia el dia de la cirugia."""
    if poliza.estado != "vigente":
        return ResultadoVigencia(
            vigente=False,
            estado=poliza.estado,
            detalle=MOTIVO_ESTADO.get(poliza.estado, f"Estado de poliza: {poliza.estado}."),
        )
    if fecha < poliza.inicio_vigencia:
        return ResultadoVigencia(
            vigente=False,
            estado="no_iniciada",
            detalle=(
                f"La vigencia empieza el {poliza.inicio_vigencia:%d/%m/%Y}, "
                f"posterior a la fecha solicitada ({fecha:%d/%m/%Y})."
            ),
        )
    if fecha > poliza.fin_vigencia:
        return ResultadoVigencia(
            vigente=False,
            estado="vencida",
            detalle=f"La vigencia termino el {poliza.fin_vigencia:%d/%m/%Y}.",
        )
    return ResultadoVigencia(
        vigente=True,
        estado="vigente",
        detalle=(
            f"Poliza vigente del {poliza.inicio_vigencia:%d/%m/%Y} "
            f"al {poliza.fin_vigencia:%d/%m/%Y}."
        ),
    )


class ResultadoCarencia(BaseModel):
    cumple: bool
    dias_afiliado: int
    carencia_exigida: int
    dias_faltantes: int
    fecha_habilitacion: date
    exonerada_por_emergencia: bool
    detalle: str


def evaluar_carencia(
    poliza: Poliza,
    procedimiento: Procedimiento,
    fecha_cirugia: date,
    es_emergencia: bool = False,
) -> ResultadoCarencia:
    """
    Carencia: dias de afiliacion exigidos antes de poder usar el beneficio.

    Se cuenta desde el inicio de vigencia hasta la fecha de cirugia, y depende
    del plan. Una urgencia o accidente exonera la carencia: es la excepcion
    estandar en gastos medicos mayores, y sin ella el agente rechazaria
    apendicitis agudas.
    """
    exigida = procedimiento.carencia_para(poliza.plan)
    dias = (fecha_cirugia - poliza.inicio_vigencia).days
    habilitacion = poliza.inicio_vigencia + timedelta(days=exigida)
    faltantes = max(0, exigida - dias)

    if es_emergencia:
        return ResultadoCarencia(
            cumple=True,
            dias_afiliado=dias,
            carencia_exigida=exigida,
            dias_faltantes=faltantes,
            fecha_habilitacion=habilitacion,
            exonerada_por_emergencia=True,
            detalle=(
                f"Atencion de urgencia: la carencia de {exigida} dias no aplica. "
                f"El asegurado lleva {dias} dias de afiliacion."
            ),
        )

    if faltantes == 0:
        detalle = (
            f"Cumple: {dias} dias de afiliacion frente a los {exigida} que exige "
            f"el plan {NOMBRE_PLAN[poliza.plan]}."
        )
    else:
        detalle = (
            f"No cumple: lleva {dias} dias de afiliacion y el plan "
            f"{NOMBRE_PLAN[poliza.plan]} exige {exigida}. Faltan {faltantes} dias; "
            f"el beneficio queda habilitado el {habilitacion:%d/%m/%Y}."
        )

    return ResultadoCarencia(
        cumple=faltantes == 0,
        dias_afiliado=dias,
        carencia_exigida=exigida,
        dias_faltantes=faltantes,
        fecha_habilitacion=habilitacion,
        exonerada_por_emergencia=False,
        detalle=detalle,
    )


class ResultadoCobertura(BaseModel):
    cubierto: bool
    porcentaje: int
    excluido: bool
    detalle: str


def evaluar_cobertura(poliza: Poliza, procedimiento: Procedimiento) -> ResultadoCobertura:
    """Exclusion absoluta primero; despues, si el plan contratado lo cubre."""
    if procedimiento.exclusion:
        return ResultadoCobertura(
            cubierto=False,
            porcentaje=0,
            excluido=True,
            detalle=f"Procedimiento excluido de la cobertura: {procedimiento.exclusion}",
        )

    porcentaje = procedimiento.cobertura_para(poliza.plan)
    if porcentaje <= 0:
        return ResultadoCobertura(
            cubierto=False,
            porcentaje=0,
            excluido=False,
            detalle=(
                f"El plan {NOMBRE_PLAN[poliza.plan]} no incluye "
                f"{procedimiento.nombre} (CPT {procedimiento.cpt})."
            ),
        )

    return ResultadoCobertura(
        cubierto=True,
        porcentaje=porcentaje,
        excluido=False,
        detalle=(
            f"{procedimiento.nombre} (CPT {procedimiento.cpt}) esta cubierto al "
            f"{porcentaje}% en el plan {NOMBRE_PLAN[poliza.plan]}."
        ),
    )


class ResultadoDocumentos(BaseModel):
    completo: bool
    requeridos: list[str]
    adjuntos: list[str]
    faltantes: list[str]
    detalle: str


def evaluar_documentos(
    procedimiento: Procedimiento, documentos_adjuntos: list[str]
) -> ResultadoDocumentos:
    """
    Diferencia entre lo que el procedimiento exige y lo que el hospital adjunto.

    La comparacion es normalizada porque el nombre del documento lo teclea una
    persona en el hospital y "Estudio de imagenes" y "estudio de imágenes" son
    el mismo papel.
    """
    indice = {normalizar(d): d for d in documentos_adjuntos}
    faltantes = [
        req for req in procedimiento.documentos_requeridos if normalizar(req) not in indice
    ]

    if not faltantes:
        detalle = (
            f"Expediente completo: {len(procedimiento.documentos_requeridos)} documentos exigidos."
        )
    else:
        detalle = (
            f"Faltan {len(faltantes)} de "
            f"{len(procedimiento.documentos_requeridos)} documentos exigidos."
        )

    return ResultadoDocumentos(
        completo=not faltantes,
        requeridos=list(procedimiento.documentos_requeridos),
        adjuntos=list(documentos_adjuntos),
        faltantes=faltantes,
        detalle=detalle,
    )


class ResultadoPreexistencia(BaseModel):
    hay_indicios: bool
    declaradas: list[str]
    detectadas: list[str]
    no_declaradas: list[str]
    detalle: str


def evaluar_preexistencia(
    poliza: Poliza, condiciones_detectadas: list[str]
) -> ResultadoPreexistencia:
    """
    Compara lo que el modelo leyo en la narrativa con lo que el asegurado declaro.

    El juicio clinico ("este relato sugiere una condicion previa") es del modelo;
    la comparacion contra lo declarado es de Python. Una preexistencia declarada
    esta cubierta; una que aparece en el informe y no en la poliza no se rechaza
    sola: se manda a revision medica, que es lo que haria un auditor humano.
    """
    declaradas_norm = [normalizar(d) for d in poliza.preexistencias_declaradas]
    no_declaradas = [
        cond
        for cond in condiciones_detectadas
        if not any(dec in normalizar(cond) or normalizar(cond) in dec for dec in declaradas_norm)
    ]

    if not condiciones_detectadas:
        detalle = "El informe no menciona condiciones previas relevantes."
    elif not no_declaradas:
        detalle = "Las condiciones del informe ya estaban declaradas en la poliza."
    else:
        detalle = "Condiciones no declaradas en la poliza: " + ", ".join(no_declaradas) + "."

    return ResultadoPreexistencia(
        hay_indicios=bool(no_declaradas),
        declaradas=list(poliza.preexistencias_declaradas),
        detectadas=list(condiciones_detectadas),
        no_declaradas=no_declaradas,
        detalle=detalle,
    )


class Expediente(BaseModel):
    """Las cinco verificaciones reunidas, listas para decidir el veredicto."""

    vigencia: ResultadoVigencia
    carencia: ResultadoCarencia
    cobertura: ResultadoCobertura
    documentos: ResultadoDocumentos
    preexistencia: ResultadoPreexistencia


def construir_expediente(
    poliza: Poliza,
    procedimiento: Procedimiento,
    informe: InformeMedico,
    condiciones_detectadas: list[str] | None = None,
) -> Expediente:
    """Corre las cinco reglas de una vez sobre un caso concreto."""
    return Expediente(
        vigencia=evaluar_vigencia(poliza, informe.fecha_cirugia_propuesta),
        carencia=evaluar_carencia(
            poliza, procedimiento, informe.fecha_cirugia_propuesta, informe.es_emergencia
        ),
        cobertura=evaluar_cobertura(poliza, procedimiento),
        documentos=evaluar_documentos(procedimiento, informe.documentos_adjuntos),
        preexistencia=evaluar_preexistencia(poliza, condiciones_detectadas or []),
    )
