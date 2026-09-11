import { Outlet } from 'react-router';
import { BarraMovil, Sidebar } from '@/components/layout/Sidebar';
import { project } from '@/lib/project';

export function AppShell() {
  return (
    <div className="bg-background text-foreground">
      <Sidebar />

      {/* La columna ocupa la altura de la pantalla como minimo, asi el pie
          queda abajo del todo aunque la pagina tenga poco contenido. */}
      <div className="flex min-h-dvh flex-col lg:pl-60">
        <BarraMovil />

        {/* flex para que una pagina pueda pedir el alto disponible con h-full
            y repartirlo entre sus secciones. */}
        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 pt-9 pb-5 sm:px-6 lg:px-10">
          <Outlet />
        </main>

        <footer className="mx-auto w-full max-w-7xl px-4 pb-4 sm:px-6 lg:px-10">
          <p className="flex flex-wrap gap-x-3 gap-y-1 border-t pt-4 text-xs text-muted-foreground">
            <span>{project.tagline}</span>
            <span aria-hidden>·</span>
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="/api/docs"
              target="_blank"
              rel="noreferrer"
            >
              documentación de la API
            </a>
            <span aria-hidden>·</span>
            <a
              className="text-primary underline-offset-4 hover:underline"
              href={project.repoUrl}
              target="_blank"
              rel="noreferrer"
            >
              código fuente
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
