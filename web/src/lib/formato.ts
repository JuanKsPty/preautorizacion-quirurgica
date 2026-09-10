import type { EstadoChequeo, NivelPlan, Veredicto } from '@/types/api';

/** Panama usa el balboa a la par con el dolar; se escribe B/. */
export function dinero(valor: number): string {
  return `B/. ${valor.toLocaleString('es-PA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fecha(valor: Date): string {
  return valor.toLocaleDateString('es-PA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function fechaHora(valor: Date): string {
  return valor.toLocaleString('es-PA', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Segundos con un decimal: el numero que contrasta con "horas o dias". */
export function segundos(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

export const NOMBRE_PLAN: Record<NivelPlan, string> = {
  basico: 'Básico',
  preferente: 'Preferente',
  ejecutivo: 'Ejecutivo',
};

export const ESTADO_POLIZA: Record<string, string> = {
  vigente: 'Vigente',
  en_mora: 'En mora',
  vencida: 'Vencida',
  cancelada: 'Cancelada',
};

interface EstiloVeredicto {
  etiqueta: string;
  /** Que significa, en una frase, para quien no conoce la taxonomia. */
  glosa: string;
  clases: string;
  punto: string;
}

export const VEREDICTO: Record<Veredicto, EstiloVeredicto> = {
  APROBADO: {
    etiqueta: 'Aprobado',
    glosa: 'La cirugía queda pre-autorizada.',
    clases: 'bg-exito-fondo text-exito',
    punto: 'bg-exito',
  },
  APROBADO_CON_CONDICIONES: {
    etiqueta: 'Aprobado con condiciones',
    glosa: 'Procede, pero con salvedades sobre el monto que cubre la aseguradora.',
    clases: 'bg-alerta-fondo text-alerta',
    punto: 'bg-alerta',
  },
  DOCUMENTOS_FALTANTES: {
    etiqueta: 'Faltan documentos',
    glosa: 'No se puede resolver todavía: falta documentación del expediente.',
    clases: 'bg-info-fondo text-info',
    punto: 'bg-info',
  },
  REVISION_MEDICA: {
    etiqueta: 'Revisión médica',
    glosa: 'Pasa a un auditor médico humano. No es un rechazo.',
    clases: 'bg-revision-fondo text-revision',
    punto: 'bg-revision',
  },
  RECHAZADO: {
    etiqueta: 'Rechazado',
    glosa: 'No procede según las condiciones de la póliza.',
    clases: 'bg-rechazo-fondo text-rechazo',
    punto: 'bg-rechazo',
  },
};

export const CHEQUEO: Record<EstadoChequeo, { etiqueta: string; clases: string }> = {
  conforme: { etiqueta: 'Conforme', clases: 'text-exito' },
  no_conforme: { etiqueta: 'No conforme', clases: 'text-rechazo' },
  advertencia: { etiqueta: 'Con salvedad', clases: 'text-alerta' },
  no_aplica: { etiqueta: 'No aplica', clases: 'text-muted-foreground' },
};

/** Nombres de herramienta en lenguaje de negocio, para la linea de tiempo. */
export const HERRAMIENTA: Record<string, string> = {
  consultar_poliza: 'Lee la póliza',
  consultar_informe: 'Lee el informe médico',
  buscar_procedimiento: 'Busca el procedimiento en el catálogo',
  registrar_analisis_clinico: 'Registra el análisis clínico',
  seleccionar_procedimiento: 'Fija el código CPT',
  evaluar_expediente: 'Aplica las condiciones de la póliza',
  emitir_dictamen: 'Emite el dictamen',
};
