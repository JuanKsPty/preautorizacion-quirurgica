import { CopyIcon, FileTextIcon } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { VeredictoBadge } from '@/components/dictamen/VeredictoBadge';
import { ListaChequeos } from '@/components/dictamen/ListaChequeos';
import { TablaDesglose } from '@/components/dictamen/TablaDesglose';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { VEREDICTO, segundos } from '@/lib/formato';
import type { Dictamen } from '@/types/api';

interface Props {
  dictamen: Dictamen;
  msTotal: number | null;
}

export function TarjetaDictamen({ dictamen, msTotal }: Props) {
  const [verTecnica, setVerTecnica] = useState(false);
  const estilo = VEREDICTO[dictamen.veredicto];

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(dictamen.carta_paciente);
      toast.success('Resolución copiada');
    } catch {
      toast.error('El navegador no permitió copiar');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-3 text-base">
          <VeredictoBadge veredicto={dictamen.veredicto} tamano="grande" />
          <span className="font-mono text-sm font-normal text-muted-foreground">
            {dictamen.folio}
          </span>
          {msTotal !== null && (
            // El numero que importa: el proceso manual toma horas o dias.
            <span className="ml-auto text-sm font-normal text-muted-foreground">
              resuelto en <span className="tabular-nums font-medium">{segundos(msTotal)}</span>
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        <p className="text-sm text-muted-foreground">{estilo.glosa}</p>

        {(dictamen.cpt_identificado || dictamen.cie10_identificado) && (
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <Dato termino="Procedimiento identificado" valor={dictamen.procedimiento_identificado} />
            <Dato termino="Código CPT" valor={dictamen.cpt_identificado} mono />
            <Dato termino="Diagnóstico CIE-10" valor={dictamen.cie10_identificado} mono />
          </dl>
        )}

        {dictamen.documentos_faltantes.length > 0 && (
          <section className="rounded-md bg-info-fondo p-4">
            <h3 className="text-sm font-medium text-info">
              El hospital debe enviar {dictamen.documentos_faltantes.length}{' '}
              {dictamen.documentos_faltantes.length === 1 ? 'documento' : 'documentos'}
            </h3>
            <ul className="mt-2 space-y-1 text-sm">
              {dictamen.documentos_faltantes.map((documento) => (
                <li key={documento} className="flex items-start gap-2">
                  <FileTextIcon className="mt-0.5 size-3.5 shrink-0 text-info" aria-hidden />
                  {documento}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">
              Al recibirlos, la solicitud se vuelve a evaluar automáticamente.
            </p>
          </section>
        )}

        <section className="space-y-3">
          <h3 className="text-sm font-medium">Verificaciones</h3>
          <ListaChequeos chequeos={dictamen.chequeos} />
        </section>

        {dictamen.desglose && (
          <section className="space-y-3">
            <h3 className="text-sm font-medium">Cómo se reparte el costo</h3>
            <TablaDesglose desglose={dictamen.desglose} />
          </section>
        )}

        {dictamen.carta_paciente && (
          <section className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-medium">Resolución para el paciente</h3>
              <Button variant="ghost" size="sm" onClick={() => void copiar()}>
                <CopyIcon /> Copiar
              </Button>
            </div>
            <p className="rounded-md bg-muted/60 p-4 text-sm whitespace-pre-wrap">
              {dictamen.carta_paciente}
            </p>
          </section>
        )}

        {dictamen.justificacion_tecnica && (
          <section className="space-y-2">
            <button
              type="button"
              onClick={() => setVerTecnica((previo) => !previo)}
              aria-expanded={verTecnica}
              className="text-sm font-medium hover:text-foreground/80"
            >
              Justificación técnica para el auditor {verTecnica ? '−' : '+'}
            </button>
            {verTecnica && (
              <p className="rounded-md bg-muted/60 p-4 text-sm whitespace-pre-wrap">
                {dictamen.justificacion_tecnica}
              </p>
            )}
          </section>
        )}
      </CardContent>
    </Card>
  );
}

function Dato({
  termino,
  valor,
  mono = false,
}: {
  termino: string;
  valor: string | null;
  mono?: boolean;
}) {
  if (!valor) return null;
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{termino}</dt>
      <dd className={mono ? 'font-mono' : undefined}>{valor}</dd>
    </div>
  );
}
