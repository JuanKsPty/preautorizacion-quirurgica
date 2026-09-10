import { env } from '@/lib/env';

/** Error normalizado de la API: siempre trae status y un mensaje legible. */
export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  /** Se serializa a JSON automaticamente. */
  body?: unknown;
}

/**
 * FastAPI responde los errores como {"detail": "..."} y las validaciones como
 * {"detail": [{loc, msg, type}]}. Aqui lo aplanamos a un string mostrable.
 */
function extractMessage(payload: unknown, status: number): string {
  if (typeof payload === 'string' && payload.trim() !== '') return payload;

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail;

    if (typeof detail === 'string') return detail;

    if (Array.isArray(detail)) {
      const mensajes = detail
        .map((entry) => {
          if (entry && typeof entry === 'object' && 'msg' in entry) {
            const campo = 'loc' in entry && Array.isArray(entry.loc) ? entry.loc.at(-1) : null;
            return campo ? `${String(campo)}: ${String(entry.msg)}` : String(entry.msg);
          }
          return String(entry);
        })
        .filter(Boolean);
      if (mensajes.length > 0) return mensajes.join(' | ');
    }
  }

  return `La API respondio con el codigo ${status}`;
}

/** Cliente HTTP unico de la app: base URL, JSON y errores normalizados. */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}${path}`, {
      ...rest,
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    // fetch solo rechaza por fallo de red o CORS, nunca por status HTTP.
    throw new ApiError(0, 'No se pudo conectar con la API.', error);
  }

  if (response.status === 204) return undefined as T;

  const texto = await response.text();
  let payload: unknown = texto;
  if (texto) {
    try {
      payload = JSON.parse(texto);
    } catch {
      /* la API devolvio algo que no es JSON: lo dejamos como texto */
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, extractMessage(payload, response.status), payload);
  }

  return payload as T;
}

/** URL absoluta de un endpoint, para enlaces y para el stream de SSE. */
export function apiUrl(path = ''): string {
  return `${env.apiUrl}${path}`;
}
