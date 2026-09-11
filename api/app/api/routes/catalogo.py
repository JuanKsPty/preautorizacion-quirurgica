"""
El expediente: leer, crear y editar pólizas e informes médicos.

La lectura tiene respaldo local; la escritura NO. Notion es la única fuente de
verdad para escribir, y sin acceso a la fuente no se escribe: guardar en un
sitio que se pierde al reiniciar sería peor que no guardar, porque quien lo hizo
se marcharía creyendo que su registro existe.

No hay `DELETE` a propósito: borrar un informe dejaría dictámenes huérfanos en
la bitácora. Se archiva desde Notion si hace falta.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.errores import error_de_notion
from app.core.deps import EscrituraDep
from app.dominio.esquemas import (
    EstadoPoliza,
    InformeMedico,
    NivelPlan,
    Poliza,
    Procedimiento,
)
from app.dominio.reglas import normalizar
from app.repositorios.fabrica import notificar_escritura_exitosa, obtener_repositorio
from app.repositorios.notion import RegistroNoEncontrado

logger = logging.getLogger("app.catalogo")

router = APIRouter(tags=["expediente"])

PATRON_POLIZA = r"^POL-\d{4}-\d{4}$"
PATRON_INFORME = r"^INF-\d{4}-\d{4}$"

# Margen sobre la fecha del informe. Caza el 2206 tecleado por 2026, que si no
# atraviesa todas las reglas y produce un veredicto seguro y equivocado.
MAXIMO_ADELANTO = timedelta(days=730)


# ----------------------------------------------------------------- entradas


class PolizaEntrada(BaseModel):
    """Cuerpo de alta y de edición. El número no está: lo fija la ruta o se genera."""

    titular: str = Field(min_length=3, max_length=120)
    cedula: str = Field(min_length=3, max_length=30)
    plan: NivelPlan
    # Literal, no texto libre: `_a_poliza` pasa el estado TAL CUAL al Literal sin
    # reverso ni defecto, así que un «En mora» escrito aquí haría que
    # `listar_polizas()` lanzara y degradara la aplicación entera 60 segundos.
    estado: EstadoPoliza
    inicio_vigencia: date
    fin_vigencia: date
    deducible_anual: float = Field(ge=0, le=1_000_000)
    deducible_consumido: float = Field(default=0.0, ge=0)
    coaseguro_porcentaje: int = Field(ge=0, le=100)
    tope_anual: float = Field(gt=0, le=10_000_000)
    tope_consumido: float = Field(default=0.0, ge=0)
    red_preferente: bool = True
    preexistencias_declaradas: list[str] = Field(default_factory=list, max_length=30)
    dependientes: list[str] = Field(default_factory=list, max_length=20)


class PolizaNueva(PolizaEntrada):
    numero: str | None = Field(default=None, pattern=PATRON_POLIZA)


class InformeEntrada(BaseModel):
    paciente: str = Field(min_length=3, max_length=120)
    cedula: str = Field(min_length=3, max_length=30)
    numero_poliza: str = Field(pattern=PATRON_POLIZA)
    hospital: str = Field(min_length=3, max_length=100)
    medico_tratante: str = Field(min_length=3, max_length=120)
    especialidad: str = Field(min_length=3, max_length=100)
    fecha_informe: date
    fecha_cirugia_propuesta: date
    es_emergencia: bool = False
    monto_cotizado: float = Field(gt=0, le=1_000_000)
    documentos_adjuntos: list[str] = Field(default_factory=list, max_length=20)
    # Por debajo de esto el emparejador determinista no puede identificar el
    # procedimiento, así que sería un informe imposible de evaluar.
    texto: str = Field(min_length=120, max_length=40_000)


class InformeNuevo(InformeEntrada):
    codigo: str | None = Field(default=None, pattern=PATRON_INFORME)


class RespuestaPoliza(BaseModel):
    poliza: Poliza
    notion_url: str
    avisos: list[str] = Field(default_factory=list)


class RespuestaInforme(BaseModel):
    informe: InformeMedico
    notion_url: str
    avisos: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------- lectura


@router.get("/polizas", response_model=list[Poliza], summary="Listar pólizas")
async def listar_polizas() -> list[Poliza]:
    return await obtener_repositorio().listar_polizas()


@router.get("/polizas/{numero}", response_model=Poliza, summary="Ver una póliza")
async def ver_poliza(numero: str) -> Poliza:
    poliza = await obtener_repositorio().obtener_poliza(numero)
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la póliza {numero}")
    return poliza


@router.get("/informes", response_model=list[InformeMedico], summary="Listar informes médicos")
async def listar_informes() -> list[InformeMedico]:
    return await obtener_repositorio().listar_informes()


@router.get("/informes/{codigo}", response_model=InformeMedico, summary="Ver un informe médico")
async def ver_informe(codigo: str) -> InformeMedico:
    informe = await obtener_repositorio().obtener_informe(codigo)
    if informe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el informe {codigo}")
    return informe


@router.get(
    "/procedimientos",
    response_model=list[Procedimiento],
    summary="Catálogo de procedimientos con sus carencias y exclusiones",
)
async def listar_procedimientos() -> list[Procedimiento]:
    return await obtener_repositorio().listar_procedimientos()


# --------------------------------------------------------------- validacion


def _validar_poliza(entrada: PolizaEntrada) -> list[str]:
    """
    Reglas que cruzan campos. Las de un solo campo ya las cubre pydantic.

    Las tres primeras importan más de lo que parece: `deducible_pendiente` y
    `tope_disponible` hacen `max(0, ...)`, así que una violación se absorbe en
    silencio y el dinero sale mal SIN ningún error.
    """
    if entrada.fin_vigencia <= entrada.inicio_vigencia:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"El fin de vigencia ({entrada.fin_vigencia:%d/%m/%Y}) tiene que ser "
            f"posterior al inicio ({entrada.inicio_vigencia:%d/%m/%Y}).",
        )
    if entrada.deducible_consumido > entrada.deducible_anual:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El deducible consumido no puede superar al deducible anual.",
        )
    if entrada.tope_consumido > entrada.tope_anual:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La suma consumida no puede superar la suma asegurada anual.",
        )
    for dependiente in entrada.dependientes:
        if ";" in dependiente:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Los nombres de dependientes no pueden contener «;»: es el "
                "separador con el que se guardan y partiría el nombre en dos.",
            )
    return []


async def _validar_informe(
    repositorio: EscrituraDep, entrada: InformeEntrada, poliza: Poliza | None
) -> tuple[list[str], list[str]]:
    """Devuelve (documentos ya normalizados, avisos)."""
    if poliza is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"La póliza {entrada.numero_poliza} no existe. Un informe sin póliza "
            "no se puede evaluar.",
        )

    if entrada.fecha_cirugia_propuesta < entrada.fecha_informe:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"La fecha de cirugía ({entrada.fecha_cirugia_propuesta:%d/%m/%Y}) no "
            f"puede ser anterior a la del informe ({entrada.fecha_informe:%d/%m/%Y}). "
            "La carencia se cuenta contra ella y saldría negativa.",
        )
    if entrada.fecha_cirugia_propuesta > entrada.fecha_informe + MAXIMO_ADELANTO:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"La fecha de cirugía ({entrada.fecha_cirugia_propuesta:%d/%m/%Y}) está "
            "a más de dos años del informe. ¿Es un error de tecleo en el año?",
        )

    avisos: list[str] = []
    if entrada.fecha_informe > date.today() + timedelta(days=1):
        avisos.append(f"La fecha del informe ({entrada.fecha_informe:%d/%m/%Y}) está en el futuro.")

    # La cédula que no casa no se rechaza: la demostración tiene que poder crear
    # un caso equivocado a propósito.
    cedulas = {normalizar(poliza.cedula), *(normalizar(d) for d in poliza.dependientes)}
    if normalizar(entrada.cedula) not in cedulas:
        avisos.append(
            f"La cédula {entrada.cedula} no coincide con el titular ni con los "
            f"dependientes de {poliza.numero}."
        )

    documentos, avisos_docs = await _normalizar_documentos(entrada.documentos_adjuntos)
    return documentos, avisos + avisos_docs


async def _normalizar_documentos(documentos: list[str]) -> tuple[list[str], list[str]]:
    """
    Ajusta cada documento a la grafía del catálogo.

    Es la validación más valiosa de todas: `evaluar_documentos` compara cadenas
    normalizadas contra los documentos exigidos, así que «Estudio de imagenes»
    sin tilde produce DOCUMENTOS_FALTANTES sin ningún error en ninguna parte.
    Se corrige donde es barato —al guardar— y se avisa de lo que no se reconoce.
    """
    catalogo = await obtener_repositorio().listar_procedimientos()
    conocidos = {normalizar(d): d for proc in catalogo for d in proc.documentos_requeridos}

    ajustados: list[str] = []
    avisos: list[str] = []
    for documento in documentos:
        canonico = conocidos.get(normalizar(documento))
        if canonico is None:
            ajustados.append(documento)
            avisos.append(
                f"«{documento}» no está en el catálogo de documentos: se guarda tal "
                "cual y no contará como ninguno de los exigidos."
            )
        else:
            if canonico != documento:
                avisos.append(f"«{documento}» se guardó como «{canonico}».")
            ajustados.append(canonico)
    return ajustados, avisos


# ---------------------------------------------------------------- escritura


@router.post(
    "/polizas",
    response_model=RespuestaPoliza,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una póliza en Notion",
)
async def crear_poliza(
    entrada: PolizaNueva, repositorio: EscrituraDep, respuesta: Response
) -> RespuestaPoliza:
    avisos = _validar_poliza(entrada)
    try:
        async with repositorio.candado_escritura:
            numero = entrada.numero or await repositorio.siguiente_numero_poliza(
                entrada.inicio_vigencia.year
            )
            if await repositorio.existe_poliza(numero):
                raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe la póliza {numero}.")
            poliza = Poliza(numero=numero, **entrada.model_dump(exclude={"numero"}))
            url = await repositorio.crear_poliza(poliza)
    except HTTPException:
        raise
    except Exception as error:
        raise error_de_notion(error) from error

    notificar_escritura_exitosa()
    respuesta.headers["Location"] = f"/api/polizas/{numero}"
    return RespuestaPoliza(poliza=poliza, notion_url=url, avisos=avisos)


@router.put(
    "/polizas/{numero}",
    response_model=RespuestaPoliza,
    summary="Editar una póliza (reemplaza el registro entero)",
)
async def editar_poliza(
    numero: str, entrada: PolizaEntrada, repositorio: EscrituraDep
) -> RespuestaPoliza:
    avisos = _validar_poliza(entrada)
    poliza = Poliza(numero=numero, **entrada.model_dump())
    try:
        url = await repositorio.actualizar_poliza(numero, poliza)
    except RegistroNoEncontrado as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except Exception as error:
        raise error_de_notion(error) from error

    notificar_escritura_exitosa()
    return RespuestaPoliza(poliza=poliza, notion_url=url, avisos=avisos)


@router.post(
    "/informes",
    response_model=RespuestaInforme,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un informe médico en Notion",
)
async def crear_informe(
    entrada: InformeNuevo, repositorio: EscrituraDep, respuesta: Response
) -> RespuestaInforme:
    # La póliza se comprueba contra el repositorio de ESCRITURA: si se validara
    # contra la lectura y ésta estuviera degradada, se validaría contra los datos
    # de demostración y se aceptaría una póliza que no está en Notion.
    poliza = await repositorio.obtener_poliza(entrada.numero_poliza)
    documentos, avisos = await _validar_informe(repositorio, entrada, poliza)

    try:
        async with repositorio.candado_escritura:
            codigo = entrada.codigo or await repositorio.siguiente_codigo_informe(
                entrada.fecha_informe.year
            )
            if await repositorio.existe_informe(codigo):
                raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe el informe {codigo}.")
            informe = InformeMedico(
                codigo=codigo,
                **entrada.model_dump(exclude={"codigo", "documentos_adjuntos"}),
                documentos_adjuntos=documentos,
            )
            url = await repositorio.crear_informe(informe)
    except HTTPException:
        raise
    except Exception as error:
        raise error_de_notion(error) from error

    notificar_escritura_exitosa()
    respuesta.headers["Location"] = f"/api/informes/{codigo}"
    return RespuestaInforme(informe=informe, notion_url=url, avisos=avisos)


@router.put(
    "/informes/{codigo}",
    response_model=RespuestaInforme,
    summary="Editar un informe médico (reemplaza el registro y su relato)",
)
async def editar_informe(
    codigo: str, entrada: InformeEntrada, repositorio: EscrituraDep
) -> RespuestaInforme:
    poliza = await repositorio.obtener_poliza(entrada.numero_poliza)
    documentos, avisos = await _validar_informe(repositorio, entrada, poliza)
    informe = InformeMedico(
        codigo=codigo,
        **entrada.model_dump(exclude={"documentos_adjuntos"}),
        documentos_adjuntos=documentos,
    )
    try:
        url = await repositorio.actualizar_informe(codigo, informe)
    except RegistroNoEncontrado as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except Exception as error:
        raise error_de_notion(error) from error

    notificar_escritura_exitosa()
    return RespuestaInforme(informe=informe, notion_url=url, avisos=avisos)
