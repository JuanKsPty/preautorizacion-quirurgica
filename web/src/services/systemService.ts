import { apiFetch } from './http';
import type { Health, HealthDto } from '@/types/api';

export interface HealthCheck extends Health {
  /** Milisegundos que tardo la llamada. */
  latencyMs: number;
}

export async function getHealth(): Promise<HealthCheck> {
  const inicio = performance.now();
  const dto = await apiFetch<HealthDto>('/health');
  return {
    status: dto.status,
    app: dto.app,
    version: dto.version,
    environment: dto.environment,
    database: dto.database,
    iaHabilitada: dto.ia_habilitada,
    modelo: dto.modelo,
    esfuerzo: dto.esfuerzo,
    origenDatos: dto.origen_datos,
    notionHabilitado: dto.notion_habilitado,
    notionError: dto.notion_error,
    escrituraHabilitada: dto.escritura_habilitada,
    latencyMs: Math.round(performance.now() - inicio),
  };
}
