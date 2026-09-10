import { ApiError, apiUrl, tokenStore } from './http';
import type { ChatMessage } from '@/types/api';

interface StreamEvent {
  type: 'delta' | 'done' | 'error';
  text?: string;
  message?: string;
}

export interface StreamChatOptions {
  /** Se llama por cada fragmento de texto que llega del modelo. */
  onDelta: (text: string) => void;
  signal?: AbortSignal;
}

/**
 * Consume /api/chat, que responde Server-Sent Events.
 * Usamos fetch + ReadableStream en lugar de EventSource porque EventSource
 * solo sabe hacer GET y aqui necesitamos enviar el historial en un POST.
 */
export async function streamChat(
  messages: ChatMessage[],
  { onDelta, signal }: StreamChatOptions
): Promise<void> {
  const token = tokenStore.get();

  const response = await fetch(apiUrl('/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!response.ok) {
    let mensaje = `La API respondio con el codigo ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) mensaje = payload.detail;
    } catch {
      /* la respuesta de error no era JSON */
    }
    throw new ApiError(response.status, mensaje);
  }

  if (!response.body) {
    throw new ApiError(0, 'Este navegador no soporta respuestas en streaming');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  let chunk = await reader.read();
  while (!chunk.done) {
    buffer += decoder.decode(chunk.value, { stream: true });

    // Un evento SSE termina en linea vacia; el ultimo trozo puede venir cortado.
    const bloques = buffer.split('\n\n');
    buffer = bloques.pop() ?? '';

    for (const bloque of bloques) {
      const linea = bloque.split('\n').find((l) => l.startsWith('data:'));
      if (!linea) continue;

      const crudo = linea.slice('data:'.length).trim();
      if (!crudo) continue;

      let evento: StreamEvent;
      try {
        evento = JSON.parse(crudo) as StreamEvent;
      } catch {
        continue;
      }

      if (evento.type === 'delta' && evento.text) {
        onDelta(evento.text);
      } else if (evento.type === 'error') {
        throw new ApiError(500, evento.message ?? 'Error generando la respuesta');
      }
    }

    chunk = await reader.read();
  }
}
