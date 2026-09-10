import { BotIcon, Loader2Icon, SendIcon, SquareIcon, Trash2Icon, UserIcon } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

export function ChatPage() {
  const { messages, isStreaming, error, send, stop, reset } = useChat();
  const [borrador, setBorrador] = useState('');
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const enviar = () => {
    const texto = borrador;
    setBorrador('');
    void send(texto);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat IA</h1>
        <p className="text-sm text-muted-foreground">
          POST /api/chat devuelve la respuesta en streaming (Server-Sent Events), asi que el texto
          aparece token por token.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>No se pudo generar la respuesta</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="space-y-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-muted">
                <BotIcon className="size-5 text-muted-foreground" />
              </span>
              <div>
                <p className="font-medium">Escribe la primera pregunta</p>
                <p className="text-sm text-muted-foreground">
                  Necesita ANTHROPIC_API_KEY en el .env de la raiz. Sin ella la API responde con un
                  error claro y el resto de la app sigue funcionando.
                </p>
              </div>
            </div>
          ) : (
            <ul className="space-y-4">
              {messages.map((mensaje, indice) => (
                <li
                  key={`${mensaje.role}-${indice}`}
                  className={cn('flex gap-3', mensaje.role === 'user' && 'flex-row-reverse')}
                >
                  <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">
                    {mensaje.role === 'user' ? (
                      <UserIcon className="size-4" />
                    ) : (
                      <BotIcon className="size-4" />
                    )}
                  </span>
                  <div
                    className={cn(
                      'max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap',
                      mensaje.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-foreground'
                    )}
                  >
                    {mensaje.content || (
                      <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div ref={finRef} />
        </CardContent>
      </Card>

      <div className="space-y-2">
        <Textarea
          value={borrador}
          onChange={(evento) => setBorrador(evento.target.value)}
          onKeyDown={(evento) => {
            if (evento.key === 'Enter' && !evento.shiftKey) {
              evento.preventDefault();
              if (borrador.trim() && !isStreaming) enviar();
            }
          }}
          placeholder="Escribe tu mensaje y pulsa Enter (Shift+Enter para salto de linea)"
          rows={3}
          disabled={isStreaming}
        />
        <div className="flex gap-2">
          <Button onClick={enviar} disabled={isStreaming || borrador.trim() === ''}>
            <SendIcon /> Enviar
          </Button>
          {isStreaming && (
            <Button variant="outline" onClick={stop}>
              <SquareIcon /> Detener
            </Button>
          )}
          {messages.length > 0 && !isStreaming && (
            <Button variant="ghost" onClick={reset}>
              <Trash2Icon /> Limpiar
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
