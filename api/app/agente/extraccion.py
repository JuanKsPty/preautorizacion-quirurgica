"""
Prerrelleno del formulario a partir del informe en texto libre.

Es la mitad del producto que se ve: se pega lo que mandó el hospital y los
campos se rellenan solos. Pero es transcripción, no criterio — aquí no hay
aritmética ni veredicto, y el usuario revisa cada campo antes de guardar.

Dos decisiones que sostienen el diseño:

**Dos modelos, no uno.** El que ve el modelo usa SOLO `str | None`; una función
pura lo convierte a tipos. Así una fecha mal formada cuesta UN campo y no la
extracción entera. Y ninguno de esos campos lleva default, para que todos caigan
en `required` del esquema y el modelo tenga que emitir `null` explícito en vez
de callarse una clave que no supo rellenar.

**Nunca falla del todo.** Un normalizador con expresiones regulares corre
SIEMPRE, haya modelo o no: cédula, póliza, monto y fechas salen del texto sin
IA. Sin clave de Anthropic el formulario sigue prerrellenándose a medias, que es
mucho mejor que negarse a abrir.
"""

import logging
import re
import time
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.agente.ejecutor import obtener_cliente
from app.agente.herramientas import PATRON_CIE10, emparejar_por_texto
from app.core.config import settings
from app.dominio.esquemas import Procedimiento
from app.dominio.reglas import normalizar

logger = logging.getLogger("app.extraccion")

# Cedula panamena: 8-812-2043, PE-123-456, N-20-1234, E-8-99999.
PATRON_CEDULA = re.compile(r"\b(?:PE|E|N|\d{1,2})-\d{1,5}-\d{1,6}\b")
PATRON_POLIZA = re.compile(r"\bPOL-\d{4}-\d{4}\b")
PATRON_MONTO = re.compile(r"B/\.\s*([\d.,]+)")
PATRON_FECHA_LARGA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


class ExtraccionCruda(BaseModel):
    """
    Lo que se le pide al modelo.

    Todo `str | None` a proposito, y sin defaults: una fecha mal formada no
    puede tumbar la extraccion entera, y un campo omitido tiene que llegar como
    `null` explicito para poder listarlo como «no encontrado».
    """

    paciente: str | None = Field(description="Nombre completo del paciente.")
    cedula: str | None = Field(description="Cédula panameña, por ejemplo 8-812-2043.")
    numero_poliza: str | None = Field(description="Formato POL-AAAA-NNNN.")
    hospital: str | None = Field(description="Nombre del hospital o centro médico.")
    medico_tratante: str | None = Field(description="Nombre del médico que firma.")
    especialidad: str | None = Field(description="Especialidad médica.")
    fecha_informe: str | None = Field(description="AAAA-MM-DD.")
    fecha_cirugia_propuesta: str | None = Field(description="AAAA-MM-DD.")
    es_emergencia: bool | None = Field(
        description="true solo si el texto dice urgencia o emergencia."
    )
    monto_cotizado: str | None = Field(description="Solo el número, sin «B/.».")
    documentos_adjuntos: list[str] = Field(description="Documentos que el texto mencione.")
    diagnostico_presuntivo: str | None = Field(description="Diagnóstico principal.")
    cie10_presuntivo: str | None = Field(description="Código CIE-10, por ejemplo K80.1.")
    procedimiento_descrito: str | None = Field(
        description="El procedimiento tal como lo describe el médico."
    )


class ExtraccionInforme(BaseModel):
    """La misma informacion, ya tipada. Es lo que rellena el formulario."""

    paciente: str | None = None
    cedula: str | None = None
    numero_poliza: str | None = None
    hospital: str | None = None
    medico_tratante: str | None = None
    especialidad: str | None = None
    fecha_informe: date | None = None
    fecha_cirugia_propuesta: date | None = None
    es_emergencia: bool = False
    monto_cotizado: float | None = None
    documentos_adjuntos: list[str] = Field(default_factory=list)
    # Estos dos NO se guardan en el informe: el dictamen los vuelve a deducir.
    # Se devuelven para enseñar en pantalla lo que el agente entendio.
    diagnostico_presuntivo: str | None = None
    cie10_presuntivo: str | None = None
    procedimiento_descrito: str | None = None
    # Del emparejador determinista, no del modelo.
    cpt_sugerido: str | None = None


class RespuestaExtraccion(BaseModel):
    campos: ExtraccionInforme
    campos_no_encontrados: list[str] = Field(default_factory=list)
    origen: Literal["ia", "sin_ia", "ia_degradada"]
    aviso: str | None = None
    ms: int = 0


def _prompt(documentos: list[str]) -> str:
    return (
        "Extraes metadatos de un informe médico panameño para rellenar un "
        "formulario que una persona va a revisar antes de guardar.\n\n"
        "Reglas:\n"
        "- Transcribe, no interpretes. Si un dato no está EXPLÍCITO en el texto, "
        "devuelve null. Un null se corrige en dos segundos; un dato inventado "
        "llega al expediente del paciente.\n"
        "- Las fechas van en AAAA-MM-DD. El informe las escribe dd/mm/aaaa.\n"
        "- `monto_cotizado` es solo el número: «B/. 6,800.00» -> «6800.00».\n"
        "- `es_emergencia` es true solo si el texto habla de urgencia o emergencia.\n"
        "- `documentos_adjuntos`: usa EXACTAMENTE estos nombres cuando el texto "
        "mencione el documento; si menciona otro, transcríbelo tal cual:\n  "
        + "\n  ".join(documentos)
    )


def _a_fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor.strip()[:10])
    except ValueError:
        return None


def _a_numero(valor: str | None) -> float | None:
    if not valor:
        return None
    limpio = valor.replace("B/.", "").replace(" ", "").strip()
    # «12,500.00» y «12.500,00» conviven: la ultima marca es la decimal.
    ultima_coma, ultimo_punto = limpio.rfind(","), limpio.rfind(".")
    decimal = "," if ultima_coma > ultimo_punto else "."
    limpio = limpio.replace("." if decimal == "," else ",", "").replace(decimal, ".")
    try:
        numero = float(limpio)
    except ValueError:
        return None
    return numero if numero > 0 else None


def _fecha_del_texto(texto: str) -> date | None:
    """La primera fecha dd/mm/aaaa que aparezca, que suele ser la del informe."""
    encontrada = PATRON_FECHA_LARGA.search(texto)
    if not encontrada:
        return None
    dia, mes, anio = (int(g) for g in encontrada.groups())
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def normalizar_extraccion(
    cruda: ExtraccionCruda | None, texto: str, catalogo: list[Procedimiento]
) -> tuple[ExtraccionInforme, list[str]]:
    """
    Convierte, valida y rellena huecos con expresiones regulares.

    Es pura: se prueba sin cliente y sin red. Y corre SIEMPRE, incluso con
    `cruda=None`, que es el camino de «no hay clave de IA».
    """
    documentos_conocidos = {
        normalizar(d): d for proc in catalogo for d in proc.documentos_requeridos
    }

    campos = ExtraccionInforme()
    if cruda is not None:
        campos = ExtraccionInforme(
            paciente=cruda.paciente or None,
            cedula=cruda.cedula or None,
            numero_poliza=(cruda.numero_poliza or "").strip().upper() or None,
            hospital=cruda.hospital or None,
            medico_tratante=cruda.medico_tratante or None,
            especialidad=cruda.especialidad or None,
            fecha_informe=_a_fecha(cruda.fecha_informe),
            fecha_cirugia_propuesta=_a_fecha(cruda.fecha_cirugia_propuesta),
            es_emergencia=bool(cruda.es_emergencia),
            monto_cotizado=_a_numero(cruda.monto_cotizado),
            # Se ajustan a la grafia del catalogo: si no, `evaluar_documentos`
            # no los reconoceria despues.
            documentos_adjuntos=[
                documentos_conocidos.get(normalizar(d), d)
                for d in cruda.documentos_adjuntos
                if d and d.strip()
            ],
            diagnostico_presuntivo=cruda.diagnostico_presuntivo or None,
            procedimiento_descrito=cruda.procedimiento_descrito or None,
        )
        # Un CIE-10 con forma invalida se descarta: devolverlo solo meteria
        # basura en el formulario.
        codigo = (cruda.cie10_presuntivo or "").strip().upper()
        if codigo and PATRON_CIE10.match(codigo):
            campos.cie10_presuntivo = codigo

    # Huecos que el texto sí tiene, se saque o no del modelo.
    if campos.cedula is None:
        encontrada = PATRON_CEDULA.search(texto)
        campos.cedula = encontrada.group(0) if encontrada else None
    if campos.numero_poliza is None:
        encontrada = PATRON_POLIZA.search(texto)
        campos.numero_poliza = encontrada.group(0) if encontrada else None
    if campos.monto_cotizado is None:
        encontrada = PATRON_MONTO.search(texto)
        campos.monto_cotizado = _a_numero(encontrada.group(1)) if encontrada else None
    if campos.fecha_informe is None:
        campos.fecha_informe = _fecha_del_texto(texto)
    if not campos.es_emergencia:
        campos.es_emergencia = any(
            palabra in normalizar(texto) for palabra in ("urgencia", "urgente", "emergencia")
        )

    emparejado = emparejar_por_texto(catalogo, texto)
    if emparejado is not None:
        campos.cpt_sugerido = emparejado[0].cpt

    no_encontrados = [
        nombre
        for nombre in (
            "paciente",
            "cedula",
            "numero_poliza",
            "hospital",
            "medico_tratante",
            "especialidad",
            "fecha_informe",
            "fecha_cirugia_propuesta",
            "monto_cotizado",
        )
        if getattr(campos, nombre) is None
    ]
    return campos, no_encontrados


async def extraer(texto: str, catalogo: list[Procedimiento]) -> RespuestaExtraccion:
    """Prerrellena el formulario. Nunca lanza: degrada y lo dice."""
    arranque = time.monotonic()
    documentos = sorted({d for proc in catalogo for d in proc.documentos_requeridos})

    if not settings.ia_habilitada:
        campos, faltan = normalizar_extraccion(None, texto, catalogo)
        return RespuestaExtraccion(
            campos=campos,
            campos_no_encontrados=faltan,
            origen="sin_ia",
            aviso=(
                "Sin ANTHROPIC_API_KEY la extracción automática está desactivada. "
                "Se rellenó lo que se pudo leer del texto; completa el resto a mano."
            ),
            ms=round((time.monotonic() - arranque) * 1000),
        )

    try:
        cliente = obtener_cliente().with_options(timeout=settings.extraccion_timeout_segundos)
        respuesta = await cliente.messages.parse(
            model=settings.anthropic_model,
            max_tokens=2048,
            output_config={"effort": settings.anthropic_effort_extraccion},
            system=_prompt(documentos),
            messages=[{"role": "user", "content": texto[:40_000]}],
            output_format=ExtraccionCruda,
        )
        cruda = respuesta.parsed_output
        if cruda is None:
            raise ValueError("El modelo no devolvió la estructura pedida.")
    except Exception as error:
        logger.warning("La extracción con IA falló; se usa solo el texto. %s", error)
        campos, faltan = normalizar_extraccion(None, texto, catalogo)
        return RespuestaExtraccion(
            campos=campos,
            campos_no_encontrados=faltan,
            origen="ia_degradada",
            aviso=(
                "El proveedor de IA no respondió. Se rellenó lo que se pudo leer "
                "del texto; revisa y completa el resto."
            ),
            ms=round((time.monotonic() - arranque) * 1000),
        )

    campos, faltan = normalizar_extraccion(cruda, texto, catalogo)
    return RespuestaExtraccion(
        campos=campos,
        campos_no_encontrados=faltan,
        origen="ia",
        ms=round((time.monotonic() - arranque) * 1000),
    )
