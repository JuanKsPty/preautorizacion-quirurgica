import { useQuery } from '@tanstack/react-query';
import { ArrowRightIcon, CheckCircle2Icon, CircleAlertIcon, DatabaseIcon } from 'lucide-react';
import { Link } from 'react-router';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { listarInformes, listarProcedimientos } from '@/services/catalogoService';
import { getHealth } from '@/services/systemService';
import { listarDictamenes } from '@/services/preautorizacionService';
import { project } from '@/lib/project';

export function PanelPage() {
  const salud = useQuery({ queryKey: ['health'], queryFn: getHealth });
  const informes = useQuery({ queryKey: ['informes'], queryFn: listarInformes });
  const procedimientos = useQuery({ queryKey: ['procedimientos'], queryFn: listarProcedimientos });
  const dictamenes = useQuery({ queryKey: ['dictamenes'], queryFn: listarDictamenes });

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">{project.name}</h1>
        <p className="max-w-2xl text-muted-foreground">
          Hoy un paciente espera horas o días a que su seguro autorice una cirugía. Aquí el
          informe médico del hospital y la póliza de la aseguradora entran por un agente que
          resuelve en segundos: dice si el procedimiento está cubierto, si se cumple la carencia,
          cuánto paga cada parte y, si falta algo, exactamente qué falta.
        </p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Button asChild>
            <Link to="/evaluar">
              Evaluar una solicitud <ArrowRightIcon />
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/reglas">Ver las reglas publicadas</Link>
          </Button>
        </div>
      </section>

      {/* El metodo, con las cifras reales del sistema en cada paso. No son tres
          tarjetas de icono y titulo: cada paso ensena el artefacto que produce. */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Cómo resuelve un caso</h2>
        <ol className="grid gap-4 md:grid-cols-3">
          <Paso
            numero={1}
            titulo="Lee el informe en texto libre"
            detalle="El médico escribe prosa: «extirpación de la vesícula por vía laparoscópica». El agente extrae el diagnóstico, su código CIE-10, el procedimiento y la urgencia."
            cifra={informes.data ? `${informes.data.length} informes cargados` : undefined}
            cargando={informes.isPending}
          />
          <Paso
            numero={2}
            titulo="Lo mapea al catálogo"
            detalle="Esa prosa se convierte en un código CPT del catálogo de la aseguradora, con su carencia por plan, su porcentaje de cobertura y los documentos que exige."
            cifra={
              procedimientos.data ? `${procedimientos.data.length} procedimientos` : undefined
            }
            cargando={procedimientos.isPending}
          />
          <Paso
            numero={3}
            titulo="Aplica las condiciones y resuelve"
            detalle="Vigencia, carencia, cobertura, preexistencias, documentos y el reparto del costo se calculan en el servidor, no los estima el modelo. El veredicto sale de esas reglas."
            cifra={
              dictamenes.data ? `${dictamenes.data.length} dictámenes emitidos` : undefined
            }
            cargando={dictamenes.isPending}
          />
        </ol>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Estado del sistema</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {salud.isPending && <Skeleton className="h-24 w-full" />}
            {salud.isError && (
              <p className="text-rechazo">
                La API no responde. El frontend está servido, pero no hay backend detrás.
              </p>
            )}
            {salud.data && (
              <>
                <Fila
                  etiqueta="API"
                  valor={`${salud.data.status} · ${salud.data.latencyMs} ms`}
                  ok={salud.data.status === 'ok'}
                />
                <Fila etiqueta="Base de datos" valor={salud.data.database} ok={salud.data.database.includes('conectada')} />
                <Fila
                  etiqueta="Modelo"
                  valor={
                    salud.data.iaHabilitada
                      ? `${salud.data.modelo} · esfuerzo ${salud.data.esfuerzo}`
                      : 'sin clave configurada'
                  }
                  ok={salud.data.iaHabilitada}
                />
                <Fila
                  etiqueta="Origen de los datos"
                  valor={
                    salud.data.origenDatos === 'notion'
                      ? 'base de datos de Notion'
                      : 'datos de demostración locales'
                  }
                  ok={salud.data.origenDatos === 'notion'}
                  icono={<DatabaseIcon className="size-4" />}
                />
                {!salud.data.iaHabilitada && (
                  <p className="rounded-md bg-alerta-fondo p-3 text-xs text-alerta">
                    Sin <code>ANTHROPIC_API_KEY</code> el agente no puede razonar, pero el motor
                    de reglas sigue emitiendo el mismo veredicto con las mismas cifras.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Por qué el dictamen es auditable</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              <strong className="text-foreground">El modelo no calcula.</strong> Los días de
              carencia, el deducible, el coaseguro y el tope se computan en el servidor, en
              centavos enteros, y se le entregan al agente como herramientas.
            </p>
            <p>
              <strong className="text-foreground">El modelo no elige el veredicto.</strong> Lo
              decide la precedencia de las condiciones de la póliza. Si el agente escribe otro,
              la emisión se rechaza.
            </p>
            <p>
              <strong className="text-foreground">Ninguna cifra se inventa.</strong> Toda
              cantidad en balboas de la resolución tiene que haber salido de una herramienta; si
              no, no se emite.
            </p>
            <p>
              Y el proceso se ve entero: cada herramienta con sus argumentos y su resultado, para
              poder rastrear cualquier número hasta su origen.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Los ocho casos de la demostración</h2>
        <p className="text-sm text-muted-foreground">
          Cada informe cargado recorre un camino distinto: aprobación limpia, carencia
          incumplida, exclusión estética, expediente incompleto, preexistencia sin declarar,
          urgencia que exonera la carencia, suma asegurada insuficiente y póliza en mora.
        </p>
        {informes.data && (
          <div className="flex flex-wrap gap-2">
            {informes.data.map((informe) => (
              <Badge key={informe.codigo} variant="outline" className="font-mono">
                {informe.codigo}
              </Badge>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Paso({
  numero,
  titulo,
  detalle,
  cifra,
  cargando,
}: {
  numero: number;
  titulo: string;
  detalle: string;
  cifra?: string;
  cargando: boolean;
}) {
  return (
    <li className="space-y-2 rounded-lg border p-4">
      <p className="text-sm font-medium">
        <span className="mr-2 inline-flex size-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
          {numero}
        </span>
        {titulo}
      </p>
      <p className="text-sm text-muted-foreground">{detalle}</p>
      {cargando ? (
        <Skeleton className="h-4 w-28" />
      ) : (
        cifra && <p className="text-xs font-medium tabular-nums">{cifra}</p>
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
    <div className="flex items-start justify-between gap-3">
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
