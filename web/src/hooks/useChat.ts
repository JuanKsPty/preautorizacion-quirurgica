import { useCallback, useEffect, useRef, useState } from 'react';
import { streamChat } from '@/services/chatService';
import type { ChatMessage } from '@/types/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Si el componente se desmonta a mitad del stream, cortamos la peticion.
  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(
    async (contenido: string) => {
      const texto = contenido.trim();
      if (!texto || isStreaming) return;

      const historial: ChatMessage[] = [...messages, { role: 'user', content: texto }];
      // Burbuja vacia del asistente: se va llenando con cada fragmento.
      setMessages([...historial, { role: 'assistant', content: '' }]);
      setError(null);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(historial, {
          signal: controller.signal,
          onDelta: (fragmento) => {
            setMessages((previos) => {
              const copia = [...previos];
              const ultimo = copia[copia.length - 1];
              if (ultimo?.role === 'assistant') {
                copia[copia.length - 1] = { ...ultimo, content: ultimo.content + fragmento };
              }
              return copia;
            });
          },
        });
      } catch (e) {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : 'No se pudo generar la respuesta');
        // Quitamos la burbuja del asistente si quedo vacia.
        setMessages((previos) => {
          const ultimo = previos[previos.length - 1];
          return ultimo?.role === 'assistant' && ultimo.content === ''
            ? previos.slice(0, -1)
            : previos;
        });
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [messages, isStreaming]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isStreaming, error, send, stop, reset };
}
