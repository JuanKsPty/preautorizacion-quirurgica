// ---------------------------------------------------------------------------
// DTOs: lo que devuelve la API tal cual (snake_case, fechas como string).
// Modelos de dominio: lo que consume la UI (camelCase, Date).
// La conversion se hace en services/, nunca en los componentes.
// ---------------------------------------------------------------------------

export type NivelPlan = 'basico' | 'preferente' | 'ejecutivo';

export type EstadoPoliza = 'vigente' | 'en_mora' | 'vencida' | 'cancelada';

export type Veredicto =
  | 'APROBADO'
  | 'APROBADO_CON_CONDICIONES'
  | 'DOCUMENTOS_FALTANTES'
  | 'RECHAZADO'
  | 'REVISION_MEDICA';

export type EstadoChequeo = 'conforme' | 'no_conforme' | 'advertencia' | 'no_aplica';

export interface PolizaDto {
  numero: string;
  titular: string;
  cedula: string;
  plan: NivelPlan;
  estado: EstadoPoliza;
  inicio_vigencia: string;
  fin_vigencia: string;
  deducible_anual: number;
  deducible_consumido: number;
  coaseguro_porcentaje: number;
  tope_anual: number;
  tope_consumido: number;
  red_preferente: boolean;
  preexistencias_declaradas: string[];
  dependientes: string[];
}

export interface Poliza {
  numero: string;
  titular: string;
  cedula: string;
  plan: NivelPlan;
  estado: EstadoPoliza;
  inicioVigencia: Date;
  finVigencia: Date;
  deducibleAnual: number;
  deducibleConsumido: number;
  coaseguroPorcentaje: number;
  topeAnual: number;
  topeConsumido: number;
  redPreferente: boolean;
  preexistenciasDeclaradas: string[];
  dependientes: string[];
}

export interface InformeDto {
  codigo: string;
  paciente: string;
  cedula: string;
  numero_poliza: string;
  hospital: string;
  medico_tratante: string;
  especialidad: string;
  fecha_informe: string;
  fecha_cirugia_propuesta: string;
  es_emergencia: boolean;
  monto_cotizado: number;
  documentos_adjuntos: string[];
  texto: string;
}

export interface Informe {
  codigo: string;
  paciente: string;
  cedula: string;
  numeroPoliza: string;
  hospital: string;
  medicoTratante: string;
  especialidad: string;
  fechaInforme: Date;
  fechaCirugiaPropuesta: Date;
  esEmergencia: boolean;
  montoCotizado: number;
  documentosAdjuntos: string[];
  texto: string;
}

export interface ProcedimientoDto {
  cpt: string;
  nombre: string;
  sinonimos: string[];
  categoria: string;
  carencia_dias: Record<string, number>;
  cobertura_porcentaje: Record<string, number>;
  documentos_requeridos: string[];
  exclusion: string | null;
}

export interface Procedimiento {
  cpt: string;
  nombre: string;
  sinonimos: string[];
  categoria: string;
  carenciaDias: Record<NivelPlan, number>;
  coberturaPorcentaje: Record<NivelPlan, number>;
  documentosRequeridos: string[];
  exclusion: string | null;
}

export interface Chequeo {
  nombre: string;
  estado: EstadoChequeo;
  detalle: string;
}

export interface Desglose {
  monto_cotizado: number;
  cobertura_porcentaje: number;
  deducible_aplicado: number;
  coaseguro_asegurado: number;
  no_reconocido_por_plan: number;
  exceso_sobre_tope: number;
  cubierto_aseguradora: number;
  a_cargo_paciente: number;
  tope_disponible_antes: number;
  tope_disponible_despues: number;
  excede_tope: boolean;
}

/** El dictamen viaja en snake_case y se consume tal cual: es un documento, no una entidad. */
export interface Dictamen {
  folio: string;
  veredicto: Veredicto;
  resumen: string;
  numero_poliza: string;
  codigo_informe: string;
  paciente: string;
  cpt_identificado: string | null;
  procedimiento_identificado: string | null;
  cie10_identificado: string | null;
  motivos: string[];
  documentos_faltantes: string[];
  chequeos: Chequeo[];
  desglose: Desglose | null;
  carta_paciente: string;
  justificacion_tecnica: string;
}

export interface HealthDto {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: string;
  ia_habilitada: boolean;
  modelo: string;
  esfuerzo: string;
  origen_datos: string;
  notion_habilitado: boolean;
}

export interface Health {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: string;
  iaHabilitada: boolean;
  modelo: string;
  esfuerzo: string;
  origenDatos: string;
  notionHabilitado: boolean;
}

export interface DictamenRegistradoDto {
  id: number;
  folio: string;
  veredicto: Veredicto;
  numero_poliza: string;
  codigo_informe: string;
  paciente: string;
  cpt: string | null;
  procedimiento: string | null;
  monto_cotizado: number;
  cubierto_aseguradora: number;
  a_cargo_paciente: number;
  ms_total: number;
  origen_datos: string;
  notion_url: string | null;
  dictamen: Dictamen | Record<string, never>;
  created_at: string;
}

export interface DictamenRegistrado {
  id: number;
  folio: string;
  veredicto: Veredicto;
  numeroPoliza: string;
  codigoInforme: string;
  paciente: string;
  cpt: string | null;
  procedimiento: string | null;
  montoCotizado: number;
  cubiertoAseguradora: number;
  aCargoPaciente: number;
  msTotal: number;
  origenDatos: string;
  notionUrl: string | null;
  dictamen: Dictamen | null;
  createdAt: Date;
}

// ------------------------------------------------------------------ streaming

/** Eventos que emite POST /api/preautorizaciones/evaluar por SSE. */
export type EventoAgente =
  | {
      tipo: 'inicio';
      folio: string;
      modelo: string;
      esfuerzo: string;
      origen_datos: string;
      caso: {
        codigo_informe: string;
        numero_poliza: string;
        paciente: string;
        hospital: string;
      };
    }
  | { tipo: 'razonamiento'; texto: string }
  | { tipo: 'comentario'; texto: string }
  | {
      tipo: 'herramienta';
      fase: 'inicio';
      id: string;
      nombre: string;
      iteracion: number;
      argumentos: Record<string, unknown>;
    }
  | {
      tipo: 'herramienta';
      fase: 'fin';
      id: string;
      nombre: string;
      ok: boolean;
      ms: number;
      resultado?: Record<string, unknown>;
      error?: string;
    }
  | {
      tipo: 'chequeos';
      veredicto: Veredicto;
      chequeos: Chequeo[];
      desglose: Desglose | null;
    }
  | { tipo: 'dictamen'; dictamen: Dictamen; ms_total: number }
  | { tipo: 'aviso'; mensaje: string }
  | { tipo: 'error'; codigo?: string; mensaje: string }
  | { tipo: 'fin'; folio: string; veredicto: Veredicto | null };
