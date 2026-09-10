import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'next-themes';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from '@/components/AuthProvider';

// La pantalla de inicio consulta /api/health; aqui no hay API, la simulamos.
vi.mock('@/services/systemService', () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: 'ok',
    app: 'Hackathon Starter API',
    version: '1.0.0',
    environment: 'test',
    database: 'sqlite (conectada)',
    aiEnabled: false,
    latencyMs: 7,
  }),
}));

function montar(ruta: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <ThemeProvider attribute="class">
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[ruta]}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('la pantalla de inicio muestra el estado de la integracion con la API', async () => {
    montar('/');

    expect(screen.getByRole('heading', { level: 1, name: /hackathon starter/i })).toBeInTheDocument();
    expect(await screen.findByText(/API conectada en 7 ms/i)).toBeInTheDocument();
    expect(screen.getByText(/sqlite \(conectada\)/i)).toBeInTheDocument();
  });

  it('una ruta protegida redirige a login cuando no hay sesion', async () => {
    montar('/items');

    expect(await screen.findByRole('button', { name: /^entrar$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/contrasena/i)).toBeInTheDocument();
  });

  it('una ruta inexistente muestra el 404', async () => {
    montar('/no-existe');

    // La pantalla se carga con lazy(), asi que hay que esperarla.
    expect(await screen.findByText('404')).toBeInTheDocument();
  });
});
