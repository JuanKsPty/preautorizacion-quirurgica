import { CheckIcon, CircleSlashIcon, MinusIcon, TriangleAlertIcon } from 'lucide-react';
import { CHEQUEO } from '@/lib/formato';
import { cn } from '@/lib/utils';
import type { Chequeo, EstadoChequeo } from '@/types/api';

const ICONO: Record<EstadoChequeo, typeof CheckIcon> = {
  conforme: CheckIcon,
  no_conforme: CircleSlashIcon,
  advertencia: TriangleAlertIcon,
  no_aplica: MinusIcon,
};

/**
 * Los seis chequeos con su numero real a la vista.
 *
 * No es un resumen: es la traza. Cada linea dice de donde sale el veredicto, y
 * un evaluador puede comprobarla contra la tabla de reglas publicada.
 */
export function ListaChequeos({ chequeos }: { chequeos: Chequeo[] }) {
  return (
    <ul className="divide-y">
      {chequeos.map((chequeo) => {
        const estilo = CHEQUEO[chequeo.estado];
        const Icono = ICONO[chequeo.estado];
        return (
          <li key={chequeo.nombre} className="flex gap-3 py-3 first:pt-0 last:pb-0">
            <Icono className={cn('mt-0.5 size-4 shrink-0', estilo.clases)} aria-hidden />
            <div className="min-w-0 space-y-0.5">
              <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
                {chequeo.nombre}
                <span className={cn('text-xs font-normal', estilo.clases)}>
                  {estilo.etiqueta}
                </span>
              </p>
              <p className="text-sm text-muted-foreground">{chequeo.detalle}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
