import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { EstadoEscritura } from '@/hooks/useEscrituraHabilitada';

interface Props {
  estado: EstadoEscritura;
  a: string;
  children: ReactNode;
  variante?: 'default' | 'outline' | 'ghost';
  tamano?: 'default' | 'sm' | 'lg';
}

/**
 * Un enlace de alta que, cuando no se puede escribir, se queda visible pero
 * deshabilitado y explica por que.
 *
 * Esconderlo seria peor: quien busca «crear un informe» y no encuentra el boton
 * concluye que la funcion no existe, no que le falta un permiso.
 */
export function BotonEscritura({ estado, a, children, variante, tamano }: Props) {
  if (estado.habilitada) {
    return (
      <Button variant={variante} size={tamano} asChild>
        <Link to={a}>{children}</Link>
      </Button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {/* El span recibe el puntero: un <button disabled> no emite eventos de
            raton, asi que el tooltip nunca llegaria a dispararse. */}
        <span tabIndex={0} className="inline-flex">
          <Button variant={variante} size={tamano} disabled>
            {children}
          </Button>
        </span>
      </TooltipTrigger>
      {estado.motivo && <TooltipContent className="max-w-64">{estado.motivo}</TooltipContent>}
    </Tooltip>
  );
}
