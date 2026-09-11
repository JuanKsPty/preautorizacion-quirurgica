import { useQuery } from '@tanstack/react-query';
import {
  ChevronDownIcon,
  ExternalLinkIcon,
  FileDownIcon,
  InboxIcon,
  SearchIcon,
  SearchXIcon,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { TarjetaDictamen } from '@/components/dictamen/TarjetaDictamen';
import { VeredictoBadge } from '@/components/dictamen/VeredictoBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { demoModeEnabled } from '@/lib/demo-data';
import { exportarDictamenPdf } from '@/lib/exportar-pdf';
import { VEREDICTO, dinero, fechaHora, segundos } from '@/lib/formato';
import { cn } from '@/lib/utils';
import { listarDictamenes } from '@/services/preautorizacionService';
import type { DictamenRegistrado, Veredicto } from '@/types/api';

export function CasosPage() {
  const [abierto, setAbierto] = useState<number | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [filtroVeredicto, setFiltroVeredicto] = useState<Veredicto | null>(null);
  const dictamenes = useQuery({ queryKey: ['dictamenes'], queryFn: listarDictamenes });
  const esDemo = demoModeEnabled();

  const veredictosPresentes = useMemo(() => {
    const vistos = new Set<Veredicto>();
    for (const registro of dictamenes.data ?? []) vistos.add(registro.veredicto);
    return [...vistos];
  }, [dictamenes.data]);

  const filtrados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase();
    return (dictamenes.data ?? []).filter((registro) => {
      if (filtroVeredicto && registro.veredicto !== filtroVeredicto) return false;
      if (!termino) return true;
      return (
        registro.folio.toLowerCase().includes(termino) ||
        registro.paciente.toLowerCase().includes(termino) ||
        (registro.procedimiento?.toLowerCase().includes(termino) ?? false)
      );
    });
  }, [dictamenes.data, busqueda, filtroVeredicto]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Casos resueltos</h1>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm text-muted-foreground">Pulsa una fila para ver la resolución completa.</p>
          {esDemo && (
            <span className="rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground">
              Datos de prueba
            </span>
          )}
        </div>
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
        <>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative w-full min-w-[18rem] max-w-sm flex-1">
              <SearchIcon
                className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Buscar por folio, paciente o procedimiento…"
                value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value)}
                className="pl-8"
                aria-label="Buscar casos"
              />
            </div>
            <div className="flex flex-wrap gap-1.5">
              <FiltroVeredicto
                etiqueta="Todos"
                activo={filtroVeredicto === null}
                onClick={() => setFiltroVeredicto(null)}
              />
              {veredictosPresentes.map((veredicto) => (
                <FiltroVeredicto
                  key={veredicto}
                  etiqueta={VEREDICTO[veredicto].etiqueta}
                  activo={filtroVeredicto === veredicto}
                  onClick={() => setFiltroVeredicto(veredicto)}
                />
              ))}
            </div>
          </div>

          {filtrados.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-muted">
                <SearchXIcon className="size-5 text-muted-foreground" aria-hidden />
              </span>
              <p className="text-sm text-muted-foreground">
                Ningún caso coincide con la búsqueda o el filtro.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filtrados.map((registro) => (
                <Fila
                  key={registro.id}
                  registro={registro}
                  abierto={abierto === registro.id}
                  alternar={() =>
                    setAbierto((previo) => (previo === registro.id ? null : registro.id))
                  }
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FiltroVeredicto({
  etiqueta,
  activo,
  onClick,
}: {
  etiqueta: string;
  activo: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={activo}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        activo
          ? 'border-primary bg-accent text-accent-foreground'
          : 'border-border text-muted-foreground hover:text-foreground'
      )}
    >
      {etiqueta}
    </button>
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
    <Card className="relative overflow-hidden">
      {/* Riel de color: el veredicto se reconoce antes de leer la fila. */}
      <span
        className={cn('absolute inset-y-0 left-0 w-1', VEREDICTO[registro.veredicto].punto)}
        aria-hidden
      />
      <CardContent className="space-y-4 pl-5">
        <button
          type="button"
          onClick={alternar}
          aria-expanded={abierto}
          className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 text-left"
        >
          <ChevronDownIcon
            className={cn(
              'size-4 shrink-0 text-muted-foreground transition-transform',
              abierto && 'rotate-180'
            )}
            aria-hidden
          />
          <VeredictoBadge veredicto={registro.veredicto} />
          <span className="font-mono text-sm">{registro.folio}</span>
          <span className="min-w-0 truncate text-sm font-medium">{registro.paciente}</span>
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
            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            Ver el registro en Notion <ExternalLinkIcon className="size-3" />
          </a>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => exportarDictamenPdf(registro)}
          >
            <FileDownIcon /> Exportar PDF
          </Button>
        </div>

        {abierto && registro.dictamen && (
          <TarjetaDictamen dictamen={registro.dictamen} msTotal={registro.msTotal || null} />
        )}
      </CardContent>
    </Card>
  );
}
