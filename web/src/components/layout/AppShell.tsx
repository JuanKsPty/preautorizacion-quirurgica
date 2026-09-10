import { Outlet } from 'react-router';
import { Navbar } from '@/components/layout/Navbar';
import { project } from '@/lib/project';

export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t py-4">
        <p className="mx-auto flex max-w-6xl flex-wrap gap-x-3 gap-y-1 px-4 text-xs text-muted-foreground">
          <span>{project.tagline}</span>
          <span aria-hidden>·</span>
          <a className="underline hover:text-foreground" href="/api/docs" target="_blank" rel="noreferrer">
            documentación de la API
          </a>
          <span aria-hidden>·</span>
          <a className="underline hover:text-foreground" href={project.repoUrl} target="_blank" rel="noreferrer">
            código fuente
          </a>
        </p>
      </footer>
    </div>
  );
}
