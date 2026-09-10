import { BrainIcon, CheckIcon, Loader2Icon, MessageSquareIcon, WrenchIcon, XIcon } from 'lucide-react';
import { useState } from 'react';
import { HERRAMIENTA } from '@/lib/formato';
import { cn } from '@/lib/utils';
import type { Paso } from '@/hooks/usePreautorizacion';

/**
 * Lo que el agente va haciendo, en vivo.
 *
 * Que el proceso se vea no es adorno: un dictamen de seguros sin traza no es
 * auditable. Aqui se ve que herramienta pidio, con que argumentos y que le
 * devolvio, asi que cualquier cifra del dictamen se puede rastrear hasta su
 * origen. Los resultados vienen plegados para no tapar el hilo.
 */
export function LineaTiempo({ pasos, activo }: { pasos: Paso[]; activo: boolean }) {
  if (pasos.length === 0 && !activo) return null;

  return (
    <ol className="space-y-3">
      {pasos.map((paso) =>
        paso.clase === 'herramienta' ? (
          <PasoHerramienta key={paso.id} paso={paso} />
        ) : (
          <PasoTexto key={paso.id} paso={paso} />
        )
      )}
      {activo && (
        <li className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Trabajando…
        </li>
      )}
    </ol>
  );
}

function PasoTexto({ paso }: { paso: Extract<Paso, { clase: 'razonamiento' | 'comentario' }> }) {
  const esRazonamiento = paso.clase === 'razonamiento';
  const Icono = esRazonamiento ? BrainIcon : MessageSquareIcon;
  return (
    <li className="flex gap-3">
      <Icono className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <p
        className={cn(
          'min-w-0 text-sm whitespace-pre-wrap',
          esRazonamiento ? 'text-muted-foreground italic' : ''
        )}
      >
        {paso.texto}
      </p>
    </li>
  );
}

function PasoHerramienta({ paso }: { paso: Extract<Paso, { clase: 'herramienta' }> }) {
  const [abierto, setAbierto] = useState(false);
  const pendiente = paso.ok === undefined;
  const etiqueta = HERRAMIENTA[paso.nombre] ?? paso.nombre;

  return (
    <li className="flex gap-3">
      <span className="mt-0.5 shrink-0">
        {pendiente ? (
          <Loader2Icon className="size-4 animate-spin text-muted-foreground" aria-hidden />
        ) : paso.ok ? (
          <CheckIcon className="size-4 text-exito" aria-hidden />
        ) : (
          <XIcon className="size-4 text-rechazo" aria-hidden />
        )}
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <button
          type="button"
          onClick={() => setAbierto((previo) => !previo)}
          aria-expanded={abierto}
          className="flex w-full items-center gap-2 text-left text-sm font-medium hover:text-foreground/80"
        >
          <WrenchIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <span className="min-w-0 truncate">{etiqueta}</span>
          {paso.ms !== undefined && (
            <span className="ml-auto shrink-0 text-xs font-normal tabular-nums text-muted-foreground">
              {paso.ms} ms
            </span>
          )}
        </button>

        {paso.error && <p className="text-sm text-rechazo">{paso.error}</p>}

        {abierto && (
          <div className="space-y-2 rounded-md bg-muted/60 p-3 text-xs">
            {Object.keys(paso.argumentos).length > 0 && (
              <div>
                <p className="mb-1 font-medium">Le pidió</p>
                <pre className="overflow-x-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(paso.argumentos, null, 2)}
                </pre>
              </div>
            )}
            {paso.resultado && (
              <div>
                <p className="mb-1 font-medium">Le devolvió</p>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(paso.resultado, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </li>
  );
}
