import { useQuery } from '@tanstack/react-query';
import {
  ActivityIcon,
  ArrowRightIcon,
  BookOpenIcon,
  BotIcon,
  CircleCheckIcon,
  CircleXIcon,
  RefreshCwIcon,
} from 'lucide-react';
import { Link } from 'react-router';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { project } from '@/lib/project';
import { getHealth } from '@/services/systemService';

const endpoints = [
  { metodo: 'GET', ruta: '/api/health', descripcion: 'Estado de la API y de la base de datos' },
  { metodo: 'POST', ruta: '/api/auth/register', descripcion: 'Crear cuenta y recibir el JWT' },
  { metodo: 'POST', ruta: '/api/auth/login', descripcion: 'Iniciar sesion' },
  { metodo: 'GET', ruta: '/api/auth/me', descripcion: 'Usuario de la sesion actual' },
  { metodo: 'GET', ruta: '/api/items', descripcion: 'CRUD de ejemplo (requiere token)' },
  { metodo: 'POST', ruta: '/api/chat', descripcion: 'Respuesta del modelo en streaming (SSE)' },
];

const siguientesPasos = [
  'Cambia el nombre del proyecto en web/src/lib/project.ts.',
  'Renombra la entidad de ejemplo "item" por la real del proyecto.',
  'Copia el patron de ItemsPage para tus propias pantallas.',
  'Borra lo que no uses: el README dice que archivos toca en cada caso.',
];

export function HomePage() {
  const {
    data: salud,
    isPending,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: 1,
  });

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <Badge variant="secondary">Plantilla base</Badge>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{project.name}</h1>
        <p className="max-w-2xl text-muted-foreground">{project.tagline}</p>
        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/items">
              Ver el CRUD de ejemplo <ArrowRightIcon />
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/chat">
              <BotIcon /> Probar el chat IA
            </Link>
          </Button>
          <Button variant="ghost" asChild>
            <a href="/api/docs" target="_blank" rel="noreferrer">
              <BookOpenIcon /> Documentacion de la API
            </a>
          </Button>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ActivityIcon className="size-4" /> Integracion React &harr; FastAPI
          </CardTitle>
          <CardDescription>
            Esta tarjeta consulta /api/health en vivo: si esta verde, el frontend y el backend se
            estan hablando.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {isPending ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-40" />
            </div>
          ) : isError ? (
            <div className="space-y-2">
              <Badge variant="destructive">
                <CircleXIcon /> Sin conexion
              </Badge>
              <p className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : 'Error desconocido'}
              </p>
              <p className="text-sm text-muted-foreground">
                Levanta la API con <code className="rounded bg-muted px-1">pnpm dev</code> y vuelve a
                intentar.
              </p>
            </div>
          ) : (
            <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
              <div className="flex items-center justify-between gap-2 sm:col-span-2">
                <dt className="text-muted-foreground">Estado</dt>
                <dd>
                  <Badge>
                    <CircleCheckIcon /> API conectada en {salud.latencyMs} ms
                  </Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Version</dt>
                <dd className="font-medium">{salud.version}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Entorno</dt>
                <dd className="font-medium">{salud.environment}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Base de datos</dt>
                <dd className="font-medium">{salud.database}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Chat IA</dt>
                <dd className="font-medium">
                  {salud.aiEnabled ? 'habilitado' : 'sin ANTHROPIC_API_KEY'}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>

        <CardFooter>
          <Button variant="outline" size="sm" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCwIcon className={isFetching ? 'animate-spin' : undefined} />
            Volver a consultar
          </Button>
        </CardFooter>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Endpoints disponibles</CardTitle>
            <CardDescription>Todo cuelga de /api y esta documentado en /api/docs.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {endpoints.map((endpoint) => (
                <li key={`${endpoint.metodo} ${endpoint.ruta}`} className="flex flex-col gap-0.5">
                  <span className="font-mono text-xs">
                    <Badge variant="outline">{endpoint.metodo}</Badge> {endpoint.ruta}
                  </span>
                  <span className="text-muted-foreground">{endpoint.descripcion}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Siguientes pasos</CardTitle>
            <CardDescription>Para dejar la plantilla a la medida del proyecto.</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2 text-sm text-muted-foreground">
              {siguientesPasos.map((paso, indice) => (
                <li key={paso} className="flex gap-2">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-foreground">
                    {indice + 1}
                  </span>
                  {paso}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
