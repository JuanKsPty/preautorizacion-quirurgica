import { useQuery } from '@tanstack/react-query';
import { ExternalLinkIcon, InboxIcon } from 'lucide-react';
import { useState } from 'react';
import { TarjetaDictamen } from '@/components/dictamen/TarjetaDictamen';
import { VeredictoBadge } from '@/components/dictamen/VeredictoBadge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { dinero, fechaHora, segundos } from '@/lib/formato';
import { listarDictamenes } from '@/services/preautorizacionService';
import type { DictamenRegistrado } from '@/types/api';

export function CasosPage() {
  const [abierto, setAbierto] = useState<number | null>(null);
  const dictamenes = useQuery({ queryKey: ['dictamenes'], queryFn: listarDictamenes });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Casos resueltos</h1>
        <p className="text-sm text-muted-foreground">
          Cada dictamen emitido queda registrado con su traza completa. Pulsa una fila para ver
          la resolución tal como se transmitió.
        </p>
      </div>

      {dictamenes.isPending && (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {dictamenes.data?.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-muted">
              <InboxIcon className="size-5 text-muted-foreground" aria-hidden />
            </span>
            <div>
              <p className="font-medium">Todavía no se ha evaluado ningún caso</p>
              <p className="text-sm text-muted-foreground">
                Evalúa una solicitud y aparecerá aquí.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {dictamenes.data && dictamenes.data.length > 0 && (
        <div className="space-y-3">
          {dictamenes.data.map((registro) => (
            <Fila
              key={registro.id}
              registro={registro}
              abierto={abierto === registro.id}
              alternar={() => setAbierto((previo) => (previo === registro.id ? null : registro.id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Fila({
  registro,
  abierto,
  alternar,
}: {
  registro: DictamenRegistrado;
  abierto: boolean;
  alternar: () => void;
}) {
  return (
    <Card>
      <CardContent className="space-y-4 py-4">
        <button
          type="button"
          onClick={alternar}
          aria-expanded={abierto}
          className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 text-left"
        >
          <VeredictoBadge veredicto={registro.veredicto} />
          <span className="font-mono text-sm">{registro.folio}</span>
          <span className="min-w-0 truncate text-sm">{registro.paciente}</span>
          {registro.procedimiento && (
            <span className="min-w-0 truncate text-sm text-muted-foreground">
              {registro.procedimiento}
            </span>
          )}
          <span className="ml-auto flex shrink-0 items-center gap-4 text-xs text-muted-foreground">
            {registro.cubiertoAseguradora > 0 && (
              <span className="tabular-nums">{dinero(registro.cubiertoAseguradora)}</span>
            )}
            {registro.msTotal > 0 && (
              <span className="tabular-nums">{segundos(registro.msTotal)}</span>
            )}
            <span>{fechaHora(registro.createdAt)}</span>
          </span>
        </button>

        {registro.notionUrl && (
          <a
            href={registro.notionUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs underline hover:text-foreground/80"
          >
            Ver el registro en Notion <ExternalLinkIcon className="size-3" />
          </a>
        )}

        {abierto && registro.dictamen && (
          <TarjetaDictamen dictamen={registro.dictamen} msTotal={registro.msTotal || null} />
        )}
      </CardContent>
    </Card>
  );
}
