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
  texto: string;
}

export const VEREDICTO: Record<Veredicto, EstiloVeredicto> = {
  APROBADO: {
    etiqueta: 'Aprobado',
    glosa: 'La cirugía queda pre-autorizada.',
    clases: 'bg-exito-fondo text-exito',
    punto: 'bg-exito',
    texto: 'text-exito',
  },
  APROBADO_CON_CONDICIONES: {
    etiqueta: 'Aprobado con condiciones',
    glosa: 'Procede, pero con salvedades sobre el monto que cubre la aseguradora.',
    clases: 'bg-alerta-fondo text-alerta',
    punto: 'bg-alerta',
    texto: 'text-alerta',
  },
  DOCUMENTOS_FALTANTES: {
    etiqueta: 'Faltan documentos',
    glosa: 'No se puede resolver todavía: falta documentación del expediente.',
    clases: 'bg-info-fondo text-info',
    punto: 'bg-info',
    texto: 'text-info',
  },
  REVISION_MEDICA: {
    etiqueta: 'Revisión médica',
    glosa: 'Pasa a un auditor médico humano. No es un rechazo.',
    clases: 'bg-revision-fondo text-revision',
    punto: 'bg-revision',
    texto: 'text-revision',
  },
  RECHAZADO: {
    etiqueta: 'Rechazado',
    glosa: 'No procede según las condiciones de la póliza.',
    clases: 'bg-rechazo-fondo text-rechazo',
    punto: 'bg-rechazo',
    texto: 'text-rechazo',
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

/**
 * «B/. 12,500.00», «12.500,00» o «12500» -> 12500. `null` si no es un numero.
 *
 * El campo de dinero no puede ser `type="number"`: pondria flechas, la rueda del
 * raton cambiaria el valor en un formulario que trata de dinero, y rechazaria
 * «12,500.00» pegado dejando el campo vacio sin explicar por que.
 */
export function parseDinero(valor: string): number | null {
  const limpio = valor.replace(/B\/\.?/gi, '').replace(/\s/g, '').trim();
  if (!limpio) return null;
  // es-PA escribe 12,500.00 pero la gente pega 12.500,00. La ultima marca de
  // puntuacion es la decimal; el resto son separadores de millar.
  const ultimaComa = limpio.lastIndexOf(',');
  const ultimoPunto = limpio.lastIndexOf('.');
  const decimal = ultimaComa > ultimoPunto ? ',' : '.';
  const normalizado = limpio
    .replaceAll(decimal === ',' ? '.' : ',', '')
    .replace(decimal, '.');
  if (!/^-?\d*(\.\d*)?$/.test(normalizado)) return null;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

/** Como `dinero()` pero sin el «B/.»: el prefijo ya lo pinta el campo. */
export function dineroPlano(valor: number): string {
  return valor.toLocaleString('es-PA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * `Date` -> «AAAA-MM-DD» en hora LOCAL, que es lo que espera <input type="date">.
 *
 * No se puede usar `toISOString()`: convierte a UTC y en Panama (UTC-5) devuelve
 * el dia anterior. Como los servicios parsean con `new Date(\`${iso}T00:00:00\`)`,
 * que es hora local, cada poliza editada retrocederia un dia en cada guardado.
 */
export function fechaInput(valor: Date): string {
  const mes = String(valor.getMonth() + 1).padStart(2, '0');
  const dia = String(valor.getDate()).padStart(2, '0');
  return `${valor.getFullYear()}-${mes}-${dia}`;
}
