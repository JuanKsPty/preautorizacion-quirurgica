import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import { AppShell } from '@/components/layout/AppShell';
import { Skeleton } from '@/components/ui/skeleton';
import { PanelPage } from '@/pages/PanelPage';

// Solo el panel viaja en el bundle inicial; las demas se cargan al visitarlas.
const EvaluarPage = lazy(async () => ({
  default: (await import('@/pages/EvaluarPage')).EvaluarPage,
}));
const CasosPage = lazy(async () => ({
  default: (await import('@/pages/CasosPage')).CasosPage,
}));
const ReglasPage = lazy(async () => ({
  default: (await import('@/pages/ReglasPage')).ReglasPage,
}));
const ExpedientePage = lazy(async () => ({
  default: (await import('@/pages/ExpedientePage')).ExpedientePage,
}));
const InformeFormPage = lazy(async () => ({
  default: (await import('@/pages/InformeFormPage')).InformeFormPage,
}));
const PolizaFormPage = lazy(async () => ({
  default: (await import('@/pages/PolizaFormPage')).PolizaFormPage,
}));
const NotFoundPage = lazy(async () => ({
  default: (await import('@/pages/NotFoundPage')).NotFoundPage,
}));

function Cargando() {
  return (
    <div className="space-y-4" aria-busy="true">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-32 w-full" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Cargando />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<PanelPage />} />
          <Route path="evaluar" element={<EvaluarPage />} />
          {/* Una sola pagina sirve alta y edicion: cambian tres cosas (el
              titulo, si el codigo es editable y de donde salen los valores
              iniciales), y tenerlas juntas evita duplicar el panel de
              extraccion y la validacion. */}
          <Route path="expediente">
            <Route index element={<ExpedientePage />} />
            <Route path="informes/nuevo" element={<InformeFormPage />} />
            <Route path="informes/:codigo" element={<InformeFormPage />} />
            <Route path="polizas/nueva" element={<PolizaFormPage />} />
            <Route path="polizas/:numero" element={<PolizaFormPage />} />
          </Route>
          <Route path="casos" element={<CasosPage />} />
          <Route path="reglas" element={<ReglasPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
