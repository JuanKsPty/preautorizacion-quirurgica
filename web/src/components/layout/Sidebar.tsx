import {
  ChevronDownIcon,
  ClipboardCheckIcon,
  FileCheck2Icon,
  FolderPlusIcon,
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
  { to: '/expediente', label: 'Expediente', icono: FolderPlusIcon },
  { to: '/casos', label: 'Historial', icono: FileCheck2Icon },
  { to: '/reglas', label: 'Reglamento', icono: ScaleIcon },
] as const;

function Marca({ compacta = false }: { compacta?: boolean }) {
  return (
    <Link to="/" className="flex min-w-0 items-center gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-[7px] bg-primary text-primary-foreground shadow-sm">
        <StethoscopeIcon className="size-5" />
      </span>
      <span className={cn('min-w-0', compacta && 'hidden sm:block')}>
        <span className="block truncate text-[13px] font-semibold leading-tight">
          Pre-Autorización
        </span>
        <span className="block truncate text-[11px] leading-tight text-muted-foreground">
          Quirúrgica
        </span>
      </span>
    </Link>
  );
}

function EnlaceNavegacion({ enlace }: { enlace: (typeof enlaces)[number] }) {
  return (
    <NavLink
      to={enlace.to}
      end={enlace.to === '/'}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-2.5 rounded-[7px] px-2.5 py-[7px] text-[13px] tracking-wide transition-all duration-200',
          isActive
            ? 'bg-primary/10 font-medium text-foreground'
            : 'text-muted-foreground hover:bg-black/5 hover:text-foreground dark:hover:bg-white/5'
          )
      }
      style={({ isActive }) =>
        isActive
          ? {
              boxShadow: '0 0 18px -8px var(--nav-glow)',
              transition: 'box-shadow 250ms ease, background-color 250ms ease',
            }
          : undefined
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
          <enlace.icono
            className={cn(
              'size-4 shrink-0 transition-colors',
              isActive ? 'text-primary' : 'text-muted-foreground/70 group-hover:text-foreground/70'
            )}
            strokeWidth={1.7}
            aria-hidden
          />
          <span className="truncate">{enlace.label}</span>
        </>
      )}
    </NavLink>
  );
}

/** Navegacion lateral tipo workspace, conservando las cuatro rutas reales del app. */
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[260px] flex-col border-r border-border/50 bg-card/50 p-4 lg:flex">
      <div className="group mb-6 flex items-center justify-between rounded-lg px-3 py-3 transition-colors hover:bg-black/5 dark:hover:bg-white/5">
        <Marca />
        <ChevronDownIcon
          className="size-4 shrink-0 text-muted-foreground/50 transition-colors group-hover:text-foreground/70"
          strokeWidth={1.5}
          aria-hidden
        />
      </div>

      <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/50">
        Navegación
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {enlaces.map((enlace) => (
          <EnlaceNavegacion key={enlace.to} enlace={enlace} />
        ))}
      </nav>

      <div className="mt-4 border-t border-border/50 pt-3">
        <div className="flex items-center justify-between gap-2 rounded-lg px-2 py-1">
          <span className="px-1 text-[11px] text-muted-foreground">Apariencia</span>
          <ThemeToggle />
        </div>
        <p className="mt-2 px-3 text-[10px] leading-relaxed text-muted-foreground/60">
          Pre-autorizaciones quirúrgicas
        </p>
      </div>
    </aside>
  );
}

/** En pantallas estrechas la navegación conserva las mismas rutas en una fila. */
export function BarraMovil() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/50 bg-card/85 backdrop-blur lg:hidden">
      <div className="flex h-14 items-center gap-3 px-4">
        <Marca compacta />
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-border/40 px-3 py-2">
        {enlaces.map((enlace) => (
          <EnlaceNavegacion key={enlace.to} enlace={enlace} />
        ))}
      </nav>
    </header>
  );
}
