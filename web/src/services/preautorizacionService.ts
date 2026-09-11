import { ApiError, apiFetch, apiUrl } from './http';
import { DEMO_DICTAMENES, demoModeEnabled } from '@/lib/demo-data';
import type {
  DictamenRegistrado,
  DictamenRegistradoDto,
  Dictamen,
  EventoAgente,
} from '@/types/api';

const aRegistro = (dto: DictamenRegistradoDto): DictamenRegistrado => ({
  id: dto.id,
  folio: dto.folio,
  veredicto: dto.veredicto,
  numeroPoliza: dto.numero_poliza,
  codigoInforme: dto.codigo_informe,
  paciente: dto.paciente,
  cpt: dto.cpt,
  procedimiento: dto.procedimiento,
  montoCotizado: dto.monto_cotizado,
  cubiertoAseguradora: dto.cubierto_aseguradora,
  aCargoPaciente: dto.a_cargo_paciente,
  msTotal: dto.ms_total,
  origenDatos: dto.origen_datos,
  notionUrl: dto.notion_url,
  dictamen:
    dto.dictamen && 'veredicto' in dto.dictamen ? (dto.dictamen as Dictamen) : null,
  createdAt: new Date(dto.created_at),
});

export async function listarDictamenes(): Promise<DictamenRegistrado[]> {
  if (demoModeEnabled()) return DEMO_DICTAMENES;
  return (await apiFetch<DictamenRegistradoDto[]>('/preautorizaciones')).map(aRegistro);
}

export async function evaluarConReglas(codigoInforme: string): Promise<Dictamen> {
  return apiFetch<Dictamen>('/preautorizaciones/reglas', {
    method: 'POST',
    body: { codigo_informe: codigoInforme },
  });
}

export interface OpcionesEvaluacion {
  onEvento: (evento: EventoAgente) => void;
  signal?: AbortSignal;
}

/**
 * Consume el stream del agente.
 *
 * Se usa fetch + ReadableStream y no EventSource porque hace falta un POST con
 * cuerpo, y EventSource solo hace GET. Un evento SSE termina en linea en blanco
 * y el ultimo trozo de cada lectura puede venir cortado a la mitad, asi que se
 * acumula en un buffer y solo se procesan los bloques completos.
 */
export async function evaluarConAgente(
  codigoInforme: string,
  { onEvento, signal }: OpcionesEvaluacion
): Promise<void> {
  const response = await fetch(apiUrl('/preautorizaciones/evaluar'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ codigo_informe: codigoInforme }),
    signal,
  });

  if (!response.ok) {
    const texto = await response.text();
    let mensaje = `La API respondio con el codigo ${response.status}`;
    try {
      const cuerpo = JSON.parse(texto) as { detail?: string };
      if (cuerpo.detail) mensaje = cuerpo.detail;
    } catch {
      /* la respuesta no era JSON */
    }
    throw new ApiError(response.status, mensaje, texto);
  }

  if (!response.body) {
    throw new ApiError(0, 'La API no devolvio un stream.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  let chunk = await reader.read();
  while (!chunk.done) {
    buffer += decoder.decode(chunk.value, { stream: true });

    const bloques = buffer.split('\n\n');
    buffer = bloques.pop() ?? '';

    for (const bloque of bloques) {
      // Los latidos (`: latido`) no llevan linea `data:` y se ignoran solos.
      const linea = bloque.split('\n').find((l) => l.startsWith('data:'));
      if (!linea) continue;
      const crudo = linea.slice('data:'.length).trim();
      if (!crudo) continue;
      try {
        onEvento(JSON.parse(crudo) as EventoAgente);
      } catch {
        /* un evento ilegible no debe cortar el stream */
      }
    }
    chunk = await reader.read();
  }
}
