"""
Modelo del dominio de pre-autorizacion quirurgica.

Tres entradas y una salida:

    Poliza          lo que la aseguradora sabe del asegurado
    Procedimiento   la regla publicada: carencia, cobertura y documentos por plan
    InformeMedico   lo que el hospital envia, con el relato clinico en texto libre
    Dictamen        la resolucion que emite el agente

Los nombres de los planes y de los documentos son los mismos que las columnas de
Notion, para que leer de Notion no exija una tabla de traduccion.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# Nivel de plan, de menor a mayor cobertura. El orden importa: las carencias y
# los porcentajes se declaran por nivel.
NivelPlan = Literal["basico", "preferente", "ejecutivo"]

EstadoPoliza = Literal["vigente", "en_mora", "vencida", "cancelada"]

Veredicto = Literal[
    "APROBADO",
    "APROBADO_CON_CONDICIONES",
    "DOCUMENTOS_FALTANTES",
    "RECHAZADO",
    "REVISION_MEDICA",
]

EstadoChequeo = Literal["conforme", "no_conforme", "advertencia", "no_aplica"]

NOMBRE_PLAN: dict[str, str] = {
    "basico": "Básico",
    "preferente": "Preferente",
    "ejecutivo": "Ejecutivo",
}


class Poliza(BaseModel):
    """Poliza de gastos medicos mayores del asegurado."""

    numero: str
    titular: str
    cedula: str
    plan: NivelPlan
    estado: EstadoPoliza
    inicio_vigencia: date
    fin_vigencia: date
    # Deducible anual: lo primero que paga el asegurado cada ano de poliza.
    deducible_anual: float
    deducible_consumido: float = 0.0
    # Porcentaje que paga el ASEGURADO despues del deducible (lo habitual: 10-30%).
    coaseguro_porcentaje: int
    # Suma asegurada anual y cuanto se ha usado ya.
    tope_anual: float
    tope_consumido: float = 0.0
    red_preferente: bool = True
    # Diagnosticos que el asegurado declaro al contratar. Una preexistencia
    # declarada esta cubierta; una no declarada que aparece en el informe es
    # justamente lo que dispara la revision medica.
    preexistencias_declaradas: list[str] = Field(default_factory=list)
    dependientes: list[str] = Field(default_factory=list)

    @property
    def deducible_pendiente(self) -> float:
        return max(0.0, self.deducible_anual - self.deducible_consumido)

    @property
    def tope_disponible(self) -> float:
        return max(0.0, self.tope_anual - self.tope_consumido)


class Procedimiento(BaseModel):
    """
    Entrada del catalogo de procedimientos: la regla publicada.

    Es la tabla que la pantalla /reglas muestra al evaluador, para que pueda
    comprobar que el dictamen se ajusta a lo que estaba escrito de antemano.
    """

    cpt: str
    nombre: str
    # Formas en que un medico puede llamar al mismo procedimiento. El modelo las
    # usa para mapear la prosa del informe a un codigo CPT.
    sinonimos: list[str] = Field(default_factory=list)
    categoria: str
    # Dias de afiliacion exigidos antes de poder usar el beneficio, por plan.
    carencia_dias: dict[str, int]
    # Porcentaje que cubre la ASEGURADORA por plan. 0 = el plan no lo cubre.
    cobertura_porcentaje: dict[str, int]
    documentos_requeridos: list[str] = Field(default_factory=list)
    # Si viene con texto, el procedimiento esta excluido en todos los planes y
    # ese texto es el motivo que se le cita al asegurado.
    exclusion: str | None = None

    def carencia_para(self, plan: NivelPlan) -> int:
        return self.carencia_dias.get(plan, 0)

    def cobertura_para(self, plan: NivelPlan) -> int:
        return self.cobertura_porcentaje.get(plan, 0)


class InformeMedico(BaseModel):
    """Lo que el hospital manda. `texto` es el relato clinico sin estructurar."""

    codigo: str
    paciente: str
    cedula: str
    numero_poliza: str
    hospital: str
    medico_tratante: str
    especialidad: str
    fecha_informe: date
    fecha_cirugia_propuesta: date
    es_emergencia: bool = False
    monto_cotizado: float
    documentos_adjuntos: list[str] = Field(default_factory=list)
    texto: str


class Chequeo(BaseModel):
    """Una verificacion del expediente, con su numero real a la vista."""

    nombre: str
    estado: EstadoChequeo
    detalle: str


class Desglose(BaseModel):
    """Reparto del costo entre aseguradora y paciente. Todo calculado en Python."""

    monto_cotizado: float
    cobertura_porcentaje: int
    deducible_aplicado: float
    coaseguro_asegurado: float
    # Parte del gasto que el plan no reconoce por su porcentaje de cobertura.
    no_reconocido_por_plan: float
    # Lo que la aseguradora habria pagado pero no cabe en el tope anual.
    exceso_sobre_tope: float
    cubierto_aseguradora: float
    a_cargo_paciente: float
    tope_disponible_antes: float
    tope_disponible_despues: float
    excede_tope: bool


class Dictamen(BaseModel):
    """La resolucion. Es lo que se guarda en Postgres y se escribe en Notion."""

    folio: str
    veredicto: Veredicto
    resumen: str
    numero_poliza: str
    codigo_informe: str
    paciente: str
    cpt_identificado: str | None = None
    procedimiento_identificado: str | None = None
    cie10_identificado: str | None = None
    motivos: list[str] = Field(default_factory=list)
    documentos_faltantes: list[str] = Field(default_factory=list)
    chequeos: list[Chequeo] = Field(default_factory=list)
    desglose: Desglose | None = None
    carta_paciente: str = ""
    justificacion_tecnica: str = ""
