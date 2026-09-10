"""
De las cinco reglas al veredicto.

La precedencia se decide aqui, en codigo, y no en el prompt. Es la diferencia
entre un agente auditable y uno que improvisa: si dos reglas fallan a la vez, el
motivo que se le cita al asegurado tiene que ser siempre el mismo.

Orden (la primera que aplica gana):

    1. poliza no vigente / en mora / cancelada  -> RECHAZADO
    2. exclusion absoluta del procedimiento     -> RECHAZADO
    3. el plan contratado no lo cubre           -> RECHAZADO
    4. carencia no cumplida y no es urgencia    -> RECHAZADO
    5. preexistencia no declarada               -> REVISION_MEDICA
    6. faltan documentos exigidos               -> DOCUMENTOS_FALTANTES
    7. el tope anual no alcanza                 -> APROBADO_CON_CONDICIONES
    8. todo conforme                            -> APROBADO

Por que 5 va antes que 6: pedir papeles de un caso que de todas formas ira a
revision medica manda al paciente a hacer una diligencia inutil.
"""

from app.dominio.esquemas import Chequeo, Desglose, Veredicto
from app.dominio.reglas import Expediente


def _estado_preexistencia(expediente: Expediente) -> str:
    if expediente.preexistencia.hay_indicios:
        return "advertencia"
    return "conforme" if expediente.preexistencia.detectadas else "no_aplica"


def construir_chequeos(expediente: Expediente, desglose: Desglose | None) -> list[Chequeo]:
    """Los seis chequeos con su numero real, para que la UI los pueda mostrar."""
    chequeos = [
        Chequeo(
            nombre="Vigencia de la poliza",
            estado="conforme" if expediente.vigencia.vigente else "no_conforme",
            detalle=expediente.vigencia.detalle,
        ),
        Chequeo(
            nombre="Cobertura del procedimiento",
            estado="conforme" if expediente.cobertura.cubierto else "no_conforme",
            detalle=expediente.cobertura.detalle,
        ),
        Chequeo(
            nombre="Periodo de carencia",
            estado="conforme" if expediente.carencia.cumple else "no_conforme",
            detalle=expediente.carencia.detalle,
        ),
        Chequeo(
            nombre="Preexistencias",
            estado=_estado_preexistencia(expediente),
            detalle=expediente.preexistencia.detalle,
        ),
        Chequeo(
            nombre="Expediente documental",
            estado="conforme" if expediente.documentos.completo else "no_conforme",
            detalle=expediente.documentos.detalle,
        ),
    ]

    if desglose is None:
        chequeos.append(
            Chequeo(
                nombre="Suma asegurada",
                estado="no_aplica",
                detalle="No se calcula el desglose de un caso sin cobertura.",
            )
        )
    else:
        chequeos.append(
            Chequeo(
                nombre="Suma asegurada",
                estado="advertencia" if desglose.excede_tope else "conforme",
                detalle=(
                    f"Tope anual disponible B/. {desglose.tope_disponible_antes:,.2f}; "
                    f"la aseguradora cubriria B/. {desglose.cubierto_aseguradora:,.2f}"
                    + (" (el tope no alcanza al monto cotizado)." if desglose.excede_tope else ".")
                ),
            )
        )

    return chequeos


def decidir(expediente: Expediente, desglose: Desglose | None) -> tuple[Veredicto, list[str]]:
    """Devuelve el veredicto y los motivos que lo sostienen, en ese orden."""
    if not expediente.vigencia.vigente:
        return "RECHAZADO", [expediente.vigencia.detalle]

    if expediente.cobertura.excluido or not expediente.cobertura.cubierto:
        return "RECHAZADO", [expediente.cobertura.detalle]

    if not expediente.carencia.cumple:
        return "RECHAZADO", [expediente.carencia.detalle]

    if expediente.preexistencia.hay_indicios:
        return "REVISION_MEDICA", [expediente.preexistencia.detalle]

    if not expediente.documentos.completo:
        return "DOCUMENTOS_FALTANTES", [expediente.documentos.detalle]

    motivos = [expediente.cobertura.detalle, expediente.carencia.detalle]

    if desglose is not None and desglose.excede_tope:
        return "APROBADO_CON_CONDICIONES", [
            *motivos,
            "La suma asegurada disponible no cubre el monto cotizado completo.",
        ]

    return "APROBADO", motivos
