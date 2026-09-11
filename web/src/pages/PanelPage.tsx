import { useQuery } from '@tanstack/react-query';
import {
  ArrowRightIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  CircleSlashIcon,
  DatabaseIcon,
  FileTextIcon,
  GaugeIcon,
  ShieldCheckIcon,
  StethoscopeIcon,
  TimerIcon,
} from 'lucide-react';
import { useMemo } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { VEREDICTO, dinero, segundos } from '@/lib/formato';
import { cn } from '@/lib/utils';
import { listarInformes, listarProcedimientos } from '@/services/catalogoService';
import { getHealth } from '@/services/systemService';
import { listarDictamenes } from '@/services/preautorizacionService';
import type { Veredicto } from '@/types/api';

const APROBATORIOS: Veredicto[] = ['APROBADO', 'APROBADO_CON_CONDICIONES'];

/** Orden fijo: el color de un veredicto no cambia porque cambie el filtro. */
const ORDEN: Veredicto[] = [
  'APROBADO',
  'APROBADO_CON_CONDICIONES',
  'DOCUMENTOS_FALTANTES',
  'REVISION_MEDICA',
  'RECHAZADO',
];

/** El color de estado nunca viaja solo: cada veredicto lleva su icono. */
const ICONO: Record<Veredicto, typeof CheckCircle2Icon> = {
  APROBADO: CheckCircle2Icon,
  APROBADO_CON_CONDICIONES: CircleAlertIcon,
  DOCUMENTOS_FALTANTES: FileTextIcon,
  REVISION_MEDICA: StethoscopeIcon,
  RECHAZADO: CircleSlashIcon,
};

export function PanelPage() {
  const salud = useQuery({ queryKey: ['health'], queryFn: getHealth });
  const informes = useQuery({ queryKey: ['informes'], queryFn: listarInformes });
  const procedimientos = useQuery({ queryKey: ['procedimientos'], queryFn: listarProcedimientos });
  const dictamenes = useQuery({ queryKey: ['dictamenes'], queryFn: listarDictamenes });

  const metricas = useMemo(() => {
    const registros = dictamenes.data ?? [];
    const conTiempo = registros.filter((registro) => registro.msTotal > 0);
    const aprobados = registros.filter((registro) => APROBATORIOS.includes(registro.veredicto));

    const cubierto = registros.reduce((suma, registro) => suma + registro.cubiertoAseguradora, 0);
    const paciente = registros.reduce((suma, registro) => suma + registro.aCargoPaciente, 0);

    return {
      total: registros.length,
      aprobados: aprobados.length,
      tasa: registros.length > 0 ? (aprobados.length / registros.length) * 100 : 0,
      msMedio:
        conTiempo.length > 0
          ? conTiempo.reduce((suma, registro) => suma + registro.msTotal, 0) / conTiempo.length
          : null,
      cubierto,
      paciente,
      reparto: ORDEN.map((veredicto) => ({
        veredicto,
        cantidad: registros.filter((registro) => registro.veredicto === veredicto).length,
      })).filter((entrada) => entrada.cantidad > 0),
    };
  }, [dictamenes.data]);

  const hayCasos = metricas.total > 0;

  return (
    // Columna a pantalla completa: las filas de tarjetas crecen para repartirse
    // el alto sobrante en vez de amontonarse arriba y dejar hueco abajo.
    <div className="flex flex-1 flex-col gap-4">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Resumen operativo</h1>
        <div className="flex flex-wrap gap-2">
          <Button size="lg" asChild>
            <Link to="/evaluar">
              Evaluar una solicitud <ArrowRightIcon />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/casos">Ver historial</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <Metrica
          icono={<FileTextIcon className="size-4" />}
          etiqueta="Casos resueltos"
          valor={dictamenes.isPending ? null : String(metricas.total)}
        />
        <Metrica
          icono={<ShieldCheckIcon className="size-4" />}
          etiqueta="Tasa de aprobación"
          valor={dictamenes.isPending ? null : `${metricas.tasa.toFixed(0)}%`}
          pie={`${metricas.aprobados} de ${metricas.total}`}
          acento="exito"
        />
        <Metrica
          icono={<TimerIcon className="size-4" />}
          etiqueta="Tiempo medio"
          valor={
            dictamenes.isPending
              ? null
              : metricas.msMedio !== null
                ? segundos(metricas.msMedio)
                : '—'
          }
        />
        <Metrica
          icono={<GaugeIcon className="size-4" />}
          etiqueta="Monto gestionado"
          valor={dictamenes.isPending ? null : dinero(metricas.cubierto + metricas.paciente)}
        />
      </section>

      <section className="grid flex-1 gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Reparto de veredictos</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            {dictamenes.isPending && <Skeleton className="h-40 w-full" />}
            {dictamenes.data && !hayCasos && <SinDatos />}
            {hayCasos && (
              <ul className="flex flex-1 flex-col justify-between gap-3">
                {metricas.reparto.map(({ veredicto, cantidad }) => {
                  const porcentaje = (cantidad / metricas.total) * 100;
                  const Icono = ICONO[veredicto];
                  return (
                    <li key={veredicto} className="space-y-1.5">
                      <div className="flex items-center gap-2 text-sm">
                        <Icono
                          className={cn('size-4 shrink-0', VEREDICTO[veredicto].texto)}
                          aria-hidden
                        />
                        <span className="min-w-0 truncate">{VEREDICTO[veredicto].etiqueta}</span>
                        <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
                          {cantidad} · {porcentaje.toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn('h-full rounded-full', VEREDICTO[veredicto].punto)}
                          style={{ width: `${porcentaje}%` }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Reparto económico</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            {dictamenes.isPending && <Skeleton className="h-40 w-full" />}
            {dictamenes.data && !hayCasos && <SinDatos />}
            {hayCasos && (
              <>
                <div>
                  <p className="text-3xl font-semibold tracking-tight tabular-nums text-exito">
                    {((metricas.cubierto / (metricas.cubierto + metricas.paciente)) * 100).toFixed(
                      0
                    )}
                    %
                  </p>
                  <p className="text-xs text-muted-foreground">
                    del monto gestionado lo asume la aseguradora
                  </p>
                </div>

                {/* Dos segmentos con 2px de aire entre ellos, para que se lean
                    como dos cantidades y no como una barra partida. */}
                <div className="mt-auto flex h-3 w-full gap-0.5">
                  <div
                    className="rounded-full bg-exito"
                    style={{
                      width: `${(metricas.cubierto / (metricas.cubierto + metricas.paciente)) * 100}%`,
                    }}
                  />
                  <div
                    className="rounded-full bg-foreground/25"
                    style={{
                      width: `${(metricas.paciente / (metricas.cubierto + metricas.paciente)) * 100}%`,
                    }}
                  />
                </div>
                <dl className="space-y-3">
                  <Cifra
                    punto="bg-exito"
                    etiqueta="Cubre la aseguradora"
                    valor={dinero(metricas.cubierto)}
                    acento
                  />
                  <Cifra
                    punto="bg-foreground/25"
                    etiqueta="A cargo del paciente"
                    valor={dinero(metricas.paciente)}
                  />
                </dl>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid flex-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Cómo resuelve un caso</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <ol className="grid flex-1 items-stretch gap-4 sm:grid-cols-3">
              <Paso
                numero={1}
                titulo="Lee el informe"
                detalle="El médico escribe en prosa; el agente extrae diagnóstico, CIE-10 y urgencia."
                cifra={informes.data ? `${informes.data.length} informes` : undefined}
              />
              <Paso
                numero={2}
                titulo="Lo mapea al catálogo"
                detalle="Pasa a un código CPT con su carencia, cobertura y documentos exigidos."
                cifra={
                  procedimientos.data ? `${procedimientos.data.length} procedimientos` : undefined
                }
              />
              <Paso
                numero={3}
                titulo="Aplica las condiciones"
                detalle="El servidor calcula el reparto del costo. El veredicto sale de las reglas, no del modelo."
                cifra={dictamenes.data ? `${dictamenes.data.length} dictámenes` : undefined}
              />
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estado del sistema</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col justify-between gap-3 text-sm">
            {salud.isPending && <Skeleton className="h-24 w-full" />}
            {salud.isError && <p className="text-rechazo">La API no responde.</p>}
            {salud.data && (
              <>
                <Fila
                  etiqueta="API"
                  valor={`${salud.data.status} · ${salud.data.latencyMs} ms`}
                  ok={salud.data.status === 'ok'}
                />
                <Fila
                  etiqueta="Base de datos"
                  valor={
                    salud.data.database.includes('conectada') ? 'conectada' : salud.data.database
                  }
                  ok={salud.data.database.includes('conectada')}
                />
                <Fila
                  etiqueta="Modelo"
                  valor={salud.data.iaHabilitada ? salud.data.modelo : 'sin clave'}
                  ok={salud.data.iaHabilitada}
                />
                <Fila
                  etiqueta="Origen"
                  valor={salud.data.origenDatos === 'notion' ? 'Notion' : 'demostración'}
                  ok={salud.data.origenDatos === 'notion'}
                  icono={<DatabaseIcon className="size-4" />}
                />
              </>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function SinDatos() {
  return (
    <p className="py-10 text-center text-sm text-muted-foreground">
      Todavía no hay dictámenes que resumir.
    </p>
  );
}

function Cifra({
  punto,
  etiqueta,
  valor,
  acento,
}: {
  punto: string;
  etiqueta: string;
  valor: string;
  acento?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className={cn('size-2 shrink-0 rounded-full', punto)} aria-hidden />
      <dt className="min-w-0 truncate text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className={cn('ml-auto tabular-nums', acento ? 'font-medium text-exito' : 'font-medium')}>
        {valor}
      </dd>
    </div>
  );
}

function Metrica({
  icono,
  etiqueta,
  valor,
  pie,
  acento,
}: {
  icono: React.ReactNode;
  etiqueta: string;
  valor: string | null;
  pie?: string;
  acento?: 'exito';
}) {
  return (
    <Card>
      <CardContent className="space-y-1.5">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icono}
          <span className="text-xs font-medium">{etiqueta}</span>
        </div>
        {valor === null ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <p
            className={cn(
              'text-2xl font-semibold tracking-tight tabular-nums',
              acento === 'exito' && 'text-exito'
            )}
          >
            {valor}
          </p>
        )}
        {pie && <p className="text-xs text-muted-foreground">{pie}</p>}
      </CardContent>
    </Card>
  );
}

function Paso({
  numero,
  titulo,
  detalle,
  cifra,
}: {
  numero: number;
  titulo: string;
  detalle: string;
  cifra?: string;
}) {
  return (
    // Columna con la cifra empujada abajo: los tres pasos alinean su ultima
    // linea aunque el texto de cada uno ocupe distinto numero de renglones.
    <li className="flex h-full flex-col gap-1.5">
      <p className="flex items-center gap-2.5 text-sm font-medium">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent text-xs font-semibold text-accent-foreground">
          {numero}
        </span>
        {titulo}
      </p>
      <p className="text-sm text-muted-foreground">{detalle}</p>
      {cifra && (
        <p className="mt-auto pt-1 text-xs font-medium tabular-nums text-primary">{cifra}</p>
      )}
    </li>
  );
}

function Fila({
  etiqueta,
  valor,
  ok,
  icono,
}: {
  etiqueta: string;
  valor: string;
  ok: boolean;
  icono?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-muted-foreground">
        {icono}
        {etiqueta}
      </span>
      <span className="flex items-center gap-1.5 text-right">
        {ok ? (
          <CheckCircle2Icon className="size-4 shrink-0 text-exito" aria-hidden />
        ) : (
          <CircleAlertIcon className="size-4 shrink-0 text-alerta" aria-hidden />
        )}
        {valor}
      </span>
    </div>
  );
}
