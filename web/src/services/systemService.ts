import { apiFetch } from './http';
import type { Health, HealthDto } from '@/types/api';

export interface HealthCheck extends Health {
  /** Milisegundos que tardo la llamada: dato bonito para la demo. */
  latencyMs: number;
}

export async function getHealth(): Promise<HealthCheck> {
  const inicio = performance.now();
  const dto = await apiFetch<HealthDto>('/health', { auth: false });
  return {
    status: dto.status,
    app: dto.app,
    version: dto.version,
    environment: dto.environment,
    database: dto.database,
    aiEnabled: dto.ai_enabled,
    latencyMs: Math.round(performance.now() - inicio),
  };
}
