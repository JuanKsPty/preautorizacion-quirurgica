import {
  ClipboardCheckIcon,
  FileCheck2Icon,
  HouseIcon,
  ScaleIcon,
  StethoscopeIcon,
} from 'lucide-react';
import { Link, NavLink } from 'react-router';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { cn } from '@/lib/utils';

const enlaces = [
  { to: '/', label: 'Home', icono: HouseIcon },
  { to: '/evaluar', label: 'Evaluar', icono: ClipboardCheckIcon },
  { to: '/casos', label: 'Historial', icono: FileCheck2Icon },
  { to: '/reglas', label: 'Reglamento', icono: ScaleIcon },
];

function Marca({ compacta = false }: { compacta?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <StethoscopeIcon className="size-5" />
      </span>
      <span className={cn('min-w-0', compacta && 'hidden sm:block')}>
        <span className="block truncate text-sm leading-tight font-semibold">Pre-Autorización</span>
        <span className="block truncate text-xs leading-tight text-muted-foreground">
          Quirúrgica
        </span>
      </span>
    </Link>
  );
}

/**
 * Navegacion lateral: en una herramienta de trabajo el menu esta siempre a la
 * vista y no compite con el contenido, que aqui son tablas anchas.
 */
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r bg-sidebar lg:flex">
      <div className="px-4 pt-7 pb-5">
        <Marca />
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {enlaces.map((enlace) => (
          <NavLink
            key={enlace.to}
            to={enlace.to}
            end={enlace.to === '/'}
            className={({ isActive }) =>
              cn(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-accent font-medium text-accent-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    'absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary transition-opacity',
                    isActive ? 'opacity-100' : 'opacity-0'
                  )}
                  aria-hidden
                />
                <enlace.icono className="size-4 shrink-0" aria-hidden />
                {enlace.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center justify-between gap-2 border-t px-4 py-3">
        <span className="text-xs text-muted-foreground">Tema</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}

/** En pantallas estrechas la navegacion vuelve arriba, en una sola fila. */
export function BarraMovil() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur lg:hidden">
      <div className="flex h-14 items-center gap-3 px-4">
        <Marca compacta />
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
        {enlaces.map((enlace) => (
          <NavLink
            key={enlace.to}
            to={enlace.to}
            end={enlace.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-accent font-medium text-accent-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              )
            }
          >
            <enlace.icono className="size-4" aria-hidden />
            {enlace.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
