import { env } from '@/lib/env';

const TOKEN_KEY = 'hackathon.token';

/**
 * Guardamos el JWT en localStorage: es lo mas rapido de montar y sobrevive al
 * refresco de la pagina. Tradeoff conocido: es vulnerable a XSS. La alternativa
 * (cookie httpOnly + SameSite) exige manejar CSRF y es mas trabajo del que un
 * prototipo justifica. Cambiala si el proyecto maneja datos sensibles.
 */
export const tokenStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string): void => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* modo privado o storage bloqueado: seguimos en memoria */
    }
  },
  clear: (): void => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nada que limpiar */
    }
  },
};

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

let unauthorizedHandler: (() => void) | null = null;

/** El AuthProvider registra aqui que hacer cuando la API responde 401. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  /** Se serializa a JSON automaticamente. */
  body?: unknown;
  /** false para endpoints publicos (login, register, health). */
  auth?: boolean;
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

/** Cliente HTTP unico de la app: base URL, JSON, token y errores normalizados. */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, headers, ...rest } = options;
  const token = auth ? tokenStore.get() : null;

  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}${path}`, {
      ...rest,
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    // fetch solo rechaza por fallo de red o CORS, nunca por status HTTP.
    throw new ApiError(0, 'No se pudo conectar con la API. Esta corriendo en el puerto 8000?', error);
  }

  if (response.status === 401 && auth) {
    tokenStore.clear();
    unauthorizedHandler?.();
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

/** URL absoluta de un endpoint, para enlaces (por ejemplo /api/docs). */
export function apiUrl(path = ''): string {
  return `${env.apiUrl}${path}`;
}
