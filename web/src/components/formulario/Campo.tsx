import { CircleHelpIcon, SparklesIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { Label } from '@/components/ui/label';
import type { Origen } from '@/lib/origen';
import { cn } from '@/lib/utils';

interface Props {
  id: string;
  etiqueta: string;
  origen?: Origen;
  ayuda?: ReactNode;
  error?: string;
  className?: string;
  children: ReactNode;
}

export function Campo({ id, etiqueta, origen, ayuda, error, className, children }: Props) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <Label htmlFor={id}>
        {etiqueta}
        {origen === 'ia' && (
          <SparklesIcon
            className="size-3.5 text-primary"
            aria-label="Lo propuso el agente a partir del texto"
          />
        )}
        {origen === 'faltante' && (
          <CircleHelpIcon
            className="size-3.5 text-alerta"
            aria-label="El informe no lo menciona"
          />
        )}
      </Label>
      {children}
      {error ? (
        <p className="text-xs text-rechazo">{error}</p>
      ) : origen === 'faltante' ? (
        <p className="text-xs text-alerta">El informe no lo dice. Complétalo tú.</p>
      ) : ayuda ? (
        <p className="text-xs text-muted-foreground">{ayuda}</p>
      ) : null}
    </div>
  );
}