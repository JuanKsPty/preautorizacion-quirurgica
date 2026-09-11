import { Outlet } from 'react-router';
import { BarraMovil, Sidebar } from '@/components/layout/Sidebar';
import GlowHorizonFM from '@/components/ui/glow-horizon';
import { project } from '@/lib/project';

function GlowHorizonLayer() {
  return (
    <div className="pointer-events-none fixed inset-0 z-10 opacity-[0.12] transition-opacity duration-500" aria-hidden>
      <GlowHorizonFM variant="top" />
    </div>
  );
}

export function AppShell() {
  return (
    <div className="bg-background text-foreground">
      <GlowHorizonLayer />
      <Sidebar />

      {/* Marco de alto fijo: lo que sobra scrollea dentro de main, no en la
          ventana. Asi una pagina puede repartirse un alto conocido entre sus
          secciones (min-h-0 flex-1) en vez de que el documento crezca. */}
      <div className="flex h-dvh flex-col overflow-hidden lg:pl-[260px]">
        <BarraMovil />

        {/* min-h-0 deja que flex-1 calcule un alto real (no "auto"), asi el
            scroll pasa aqui adentro y una pagina puede pedir el resto con
            flex-1 min-h-0 y repartirlo entre sus secciones. */}
        <main className="scroll-fino mx-auto flex w-full max-w-7xl min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-9 pb-5 sm:px-6 lg:px-10">
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
