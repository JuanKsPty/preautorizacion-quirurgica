import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch, setUnauthorizedHandler, tokenStore } from './http';

function respuesta(body: unknown, status = 200): Response {
  const texto = typeof body === 'string' ? body : JSON.stringify(body);
  return new Response(texto, { status, headers: { 'Content-Type': 'application/json' } });
}

describe('apiFetch', () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
  });

  it('devuelve el JSON cuando la respuesta es correcta', async () => {
    vi.mocked(fetch).mockResolvedValue(respuesta({ status: 'ok' }));

    await expect(apiFetch<{ status: string }>('/health', { auth: false })).resolves.toEqual({
      status: 'ok',
    });
  });

  it('agrega el header Authorization si hay token guardado', async () => {
    tokenStore.set('token-123');
    vi.mocked(fetch).mockResolvedValue(respuesta({ ok: true }));

    await apiFetch('/items');

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.Authorization).toBe('Bearer token-123');
  });

  it('convierte el detail de FastAPI en el mensaje del error', async () => {
    vi.mocked(fetch).mockResolvedValue(respuesta({ detail: 'Credenciales invalidas' }, 401));

    await expect(apiFetch('/auth/login', { auth: false })).rejects.toThrowError(
      'Credenciales invalidas'
    );
  });

  it('aplana los errores de validacion 422 en un solo mensaje', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respuesta(
        { detail: [{ loc: ['body', 'title'], msg: 'Field required', type: 'missing' }] },
        422
      )
    );

    await expect(apiFetch('/items', { method: 'POST', body: {} })).rejects.toThrowError(
      'title: Field required'
    );
  });

  it('limpia la sesion y avisa cuando la API responde 401', async () => {
    tokenStore.set('token-viejo');
    const alExpirar = vi.fn();
    setUnauthorizedHandler(alExpirar);
    vi.mocked(fetch).mockResolvedValue(respuesta({ detail: 'Token expirado' }, 401));

    await expect(apiFetch('/auth/me')).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(alExpirar).toHaveBeenCalledOnce();
  });

  it('explica el fallo de red en lugar de propagar el error crudo de fetch', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(apiFetch('/health', { auth: false })).rejects.toThrowError(
      /No se pudo conectar con la API/
    );
  });
});
