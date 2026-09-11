import { apiFetch } from './http';
import type { Extraccion, ExtraccionDto } from '@/types/api';

/**
 * Lee un informe en texto libre y propone los campos del formulario.
 *
 * Nunca devuelve 5xx: sin clave de IA, o si el proveedor falla, responde 200
 * con lo que se puede sacar del texto y lo dice en `origen` y `aviso`.
 */
export async function extraerInforme(
  texto: string,
  signal?: AbortSignal
): Promise<Extraccion> {
  return apiFetch<ExtraccionDto>('/informes/extraer', {
    method: 'POST',
    body: { texto },
    signal,
  });
}
