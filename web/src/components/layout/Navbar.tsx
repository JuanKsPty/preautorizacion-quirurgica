import { StethoscopeIcon } from 'lucide-react';
import { Link, NavLink } from 'react-router';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { project } from '@/lib/project';
import { cn } from '@/lib/utils';

const enlaces = [
  { to: '/', label: 'Panel' },
  { to: '/evaluar', label: 'Evaluar' },
  { to: '/casos', label: 'Casos' },
  { to: '/reglas', label: 'Reglas' },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4">
        <Link to="/" className="mr-2 flex items-center gap-2 font-semibold">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <StethoscopeIcon className="size-4" />
          </span>
          <span className="hidden sm:inline">{project.name}</span>
        </Link>

        <div className="flex items-center gap-1">
          {enlaces.map((enlace) => (
            <NavLink
              key={enlace.to}
              to={enlace.to}
              end={enlace.to === '/'}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-3 py-1.5 text-sm transition-colors',
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )
              }
            >
              {enlace.label}
            </NavLink>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
