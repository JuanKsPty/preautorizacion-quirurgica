import { Outlet } from 'react-router';
import { Navbar } from '@/components/layout/Navbar';

export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <Navbar />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t py-4">
        <p className="mx-auto max-w-5xl px-4 text-xs text-muted-foreground">
          React + Vite + FastAPI &middot; documentacion de la API en{' '}
          <a className="underline hover:text-foreground" href="/api/docs" target="_blank" rel="noreferrer">
            /api/docs
          </a>
        </p>
      </footer>
    </div>
  );
}
