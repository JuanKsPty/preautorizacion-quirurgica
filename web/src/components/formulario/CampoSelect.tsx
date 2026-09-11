import { ChevronDownIcon } from 'lucide-react';
import type { SelectHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/**
 * El `select` nativo de la casa.
 *
 * Es el mismo patron que ya usa la pantalla Evaluar —`appearance-none` con un
 * chevron absoluto— pero a `h-8` para que case con la altura de `Input`: en un
 * formulario los dos van uno al lado del otro y la diferencia se nota.
 *
 * Conserva `bg-background` a proposito: la lista desplegable la pinta el
 * navegador, y con fondo transparente Chrome la dibuja mal sobre la tarjeta
 * oscura.
 */
export function CampoSelect({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        className={cn(
          'h-8 w-full appearance-none rounded-lg border border-input bg-background',
          'px-2.5 pr-9 text-sm shadow-xs transition-colors',
          'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDownIcon
        className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden
      />
    </div>
  );
}
