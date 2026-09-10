import { cn } from '@/lib/utils';
import { VEREDICTO } from '@/lib/formato';
import type { Veredicto } from '@/types/api';

interface Props {
  veredicto: Veredicto;
  tamano?: 'normal' | 'grande';
  className?: string;
}

export function VeredictoBadge({ veredicto, tamano = 'normal', className }: Props) {
  const estilo = VEREDICTO[veredicto];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full font-medium',
        estilo.clases,
        tamano === 'grande' ? 'px-4 py-1.5 text-base' : 'px-2.5 py-0.5 text-xs',
        className
      )}
    >
      <span className={cn('rounded-full', estilo.punto, tamano === 'grande' ? 'size-2.5' : 'size-1.5')} />
      {estilo.etiqueta}
    </span>
  );
}
