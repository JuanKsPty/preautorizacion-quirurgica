import { LogOutIcon, ZapIcon } from 'lucide-react';
import { Link, NavLink, useNavigate } from 'react-router';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { project } from '@/lib/project';
import { cn } from '@/lib/utils';

const enlaces = [
  { to: '/', label: 'Inicio' },
  { to: '/items', label: 'Items' },
  { to: '/chat', label: 'Chat IA' },
];

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const salir = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/" className="mr-2 flex items-center gap-2 font-semibold">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ZapIcon className="size-4" />
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
          {isAuthenticated ? (
            <>
              <span className="hidden text-sm text-muted-foreground sm:inline">{user?.email}</span>
              <Button variant="outline" size="sm" onClick={salir}>
                <LogOutIcon className="size-4" />
                Salir
              </Button>
            </>
          ) : (
            <Button size="sm" asChild>
              <Link to="/login">Entrar</Link>
            </Button>
          )}
        </div>
      </nav>
    </header>
  );
}
