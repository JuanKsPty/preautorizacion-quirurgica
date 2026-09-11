import { Loader2Icon, SaveIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  sucio: boolean;
  guardando: boolean;
  bloqueado: boolean;
  onCancelar: () => void;
  onGuardar: () => void;
  extra?: ReactNode;
}

/**
 * Pie pegajoso con las acciones.
 *
 * `z-20` no es arbitrario: la capa de brillo del AppShell va en `z-10` y sin
 * esto teñiria la barra, que quedaria mas apagada que la barra lateral.
 */
export function BarraAcciones({
  sucio,
  guardando,
  bloqueado,
  onCancelar,
  onGuardar,
  extra,
}: Props) {
  return (
    <div className="sticky bottom-0 z-20 -mx-4 mt-auto flex flex-wrap items-center gap-2 border-t bg-background/85 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-10 lg:px-10">
      {sucio && !guardando && (
        <span className="text-xs text-muted-foreground">Cambios sin guardar</span>
      )}
      <div className="ml-auto flex flex-wrap gap-2">
        <Button type="button" variant="ghost" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button type="button" size="lg" disabled={bloqueado || guardando} onClick={onGuardar}>
          {guardando ? <Loader2Icon className="animate-spin" /> : <SaveIcon />} Guardar
        </Button>
        {extra}
      </div>
    </div>
  );
}
