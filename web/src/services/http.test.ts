import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from './http';

function respuesta(cuerpo: unknown, init: ResponseInit = {}) {
  return new Response(typeof cuerpo === 'string' ? cuerpo : JSON.stringify(cuerpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
}

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('devuelve el JSON cuando la respuesta es correcta', async () => {
    vi.mocked(fetch).mockResolvedValue(respuesta({ veredicto: 'APROBADO' }));
    await expect(apiFetch('/preautorizaciones')).resolves.toEqual({ veredicto: 'APROBADO' });
  });

  it('convierte el detail de FastAPI en el mensaje del error', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respuesta({ detail: 'No existe el informe INF-0000' }, { status: 404 })
    );
    await expect(apiFetch('/informes/INF-0000')).rejects.toThrow('No existe el informe INF-0000');
  });

  it('aplana los errores de validacion 422 en un solo mensaje', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respuesta(
        {
          detail: [
            { loc: ['body', 'codigo_informe'], msg: 'String should have at least 3 characters' },
          ],
        },
        { status: 422 }
      )
    );
    await expect(apiFetch('/preautorizaciones/reglas')).rejects.toThrow(
      /codigo_informe: String should have at least 3 characters/
    );
  });

  it('explica el fallo de red en lugar de propagar el error crudo de fetch', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(apiFetch('/health')).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
    });
  });

  it('no revienta cuando la API responde 204 sin cuerpo', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiFetch('/algo')).resolves.toBeUndefined();
  });

  it('expone ApiError con el status para que la UI pueda decidir', async () => {
    vi.mocked(fetch).mockResolvedValue(respuesta({ detail: 'Falta la clave' }, { status: 503 }));
    const error: unknown = await apiFetch('/preautorizaciones/evaluar').catch(
      (e: unknown) => e
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(503);
  });
});
