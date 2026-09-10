import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppShell } from '@/components/layout/AppShell';
import { HomePage } from '@/pages/HomePage';
import { Skeleton } from '@/components/ui/skeleton';

// Solo la pantalla de inicio viaja en el bundle inicial; las demas se cargan
// cuando se visitan. Mantiene el arranque ligero al abrir la demo.
const LoginPage = lazy(async () => ({ default: (await import('@/pages/LoginPage')).LoginPage }));
const ItemsPage = lazy(async () => ({ default: (await import('@/pages/ItemsPage')).ItemsPage }));
const ChatPage = lazy(async () => ({ default: (await import('@/pages/ChatPage')).ChatPage }));
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
          <Route index element={<HomePage />} />
          <Route path="login" element={<LoginPage />} />

          {/* Todo lo que cuelgue de aqui exige sesion. */}
          <Route element={<ProtectedRoute />}>
            <Route path="items" element={<ItemsPage />} />
            <Route path="chat" element={<ChatPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
