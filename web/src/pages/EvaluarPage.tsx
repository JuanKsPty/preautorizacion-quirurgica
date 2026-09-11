import { useQuery } from '@tanstack/react-query';
import {
  AlertCircleIcon,
  ChevronDownIcon,
  FileTextIcon,
  PlayIcon,
  RotateCcwIcon,
  SquareIcon,
  WandSparklesIcon,
  ZapIcon,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { LineaTiempo } from '@/components/dictamen/LineaTiempo';
import { ListaChequeos } from '@/components/dictamen/ListaChequeos';
import { TarjetaDictamen } from '@/components/dictamen/TarjetaDictamen';
import { VeredictoBadge } from '@/components/dictamen/VeredictoBadge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { usePreautorizacion } from '@/hooks/usePreautorizacion';
import { NOMBRE_PLAN, dinero, fecha, segundos } from '@/lib/formato';
import { cn } from '@/lib/utils';
import { listarInformes, listarPolizas } from '@/services/catalogoService';

export function EvaluarPage() {
  const [codigo, setCodigo] = useState('');
  const [verRelato, setVerRelato] = useState(false);
  const {
    estado,
    cabecera,
    pasos,
    chequeos,
    veredictoPreliminar,
    dictamen,
    avisos,
    error,
    msTotal,
    msTranscurridos,
    evaluar,
    cancelar,
    reiniciar,
  } = usePreautorizacion();

  const informes = useQuery({ queryKey: ['informes'], queryFn: listarInformes });
  const polizas = useQuery({ queryKey: ['polizas'], queryFn: listarPolizas });

  const seleccionado = useMemo(
    () => informes.data?.find((informe) => informe.codigo === codigo) ?? null,
    [informes.data, codigo]
  );
  const poliza = useMemo(
    () => polizas.data?.find((p) => p.numero === seleccionado?.numeroPoliza) ?? null,
    [polizas.data, seleccionado]
  );

  const evaluando = estado === 'evaluando';
  const hayResultado = pasos.length > 0 || chequeos.length > 0 || dictamen !== null || evaluando;

  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Nueva solicitud</h1>
        <p className="text-sm text-muted-foreground">
          Elige un informe y mira cada paso del agente hasta el dictamen.
        </p>
      </div>

      <div className="grid flex-1 gap-4 lg:grid-cols-[minmax(340px,400px)_1fr] lg:grid-rows-[1fr]">
        {/* Columna de trabajo. */}
        <div className="flex flex-col">
          <Card className="flex-1">
              <CardHeader className="items-center">
                <CardTitle className="text-lg">Expediente de entrada</CardTitle>
                <CardAction>
                  {evaluando ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs tabular-nums text-muted-foreground">
                        {segundos(msTranscurridos)}
                      </span>
                      <Button variant="outline" onClick={cancelar}>
                        <SquareIcon /> Detener
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      {dictamen && (
                        <Button variant="ghost" onClick={reiniciar}>
                          <RotateCcwIcon /> Limpiar
                        </Button>
                      )}
                      <Button disabled={!codigo} onClick={() => void evaluar(codigo)}>
                        <PlayIcon /> Evaluar
                      </Button>
                    </div>
                  )}
                </CardAction>
              </CardHeader>

              <CardContent className="flex flex-1 flex-col gap-3">
                {informes.isPending ? (
                  <Skeleton className="h-10 w-full" />
                ) : (
                  <select
                    id="informe"
                    aria-label="Informe médico recibido del hospital"
                    value={codigo}
                    disabled={evaluando}
                    onChange={(evento) => {
                      setCodigo(evento.target.value);
                      setVerRelato(false);
                      reiniciar();
                    }}
                    className="h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
                  >
                    <option value="">Selecciona un informe…</option>
                    {informes.data?.map((informe) => (
                      <option key={informe.codigo} value={informe.codigo}>
                        {informe.codigo} — {informe.paciente} — {informe.especialidad}
                        {informe.esEmergencia ? ' (urgencia)' : ''}
                      </option>
                    ))}
                  </select>
                )}

                {informes.isError && (
                  <Alert variant="destructive">
                    <AlertCircleIcon />
                    <AlertTitle>No se pudieron cargar los informes</AlertTitle>
                    <AlertDescription>
                      {informes.error instanceof Error
                        ? informes.error.message
                        : 'Error desconocido'}
                    </AlertDescription>
                  </Alert>
                )}

                {/* El area de datos existe siempre, llena o vacia, y ocupa lo
                    que quede de tarjeta: al elegir un informe no cambia de alto
                    de golpe. */}
                <div className="flex-1 overflow-y-auto rounded-xl bg-muted/50 p-4">
                  {seleccionado ? (
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium">{seleccionado.paciente}</p>
                          <p className="text-xs text-muted-foreground">
                            {seleccionado.hospital} · {seleccionado.medicoTratante}
                          </p>
                        </div>
                        {seleccionado.esEmergencia && (
                          <Badge className="bg-alerta-fondo text-alerta">
                            <ZapIcon className="size-3" /> Urgencia
                          </Badge>
                        )}
                      </div>

                      <dl className="grid grid-cols-2 gap-3 text-sm">
                        <Dato
                          termino="Cirugía propuesta"
                          valor={fecha(seleccionado.fechaCirugiaPropuesta)}
                        />
                        <Dato
                          termino="Monto cotizado"
                          valor={dinero(seleccionado.montoCotizado)}
                        />
                        <Dato termino="Póliza" valor={seleccionado.numeroPoliza} />
                        <Dato termino="Plan" valor={poliza ? NOMBRE_PLAN[poliza.plan] : '—'} />
                      </dl>

                      <div>
                        <p className="mb-1.5 text-xs text-muted-foreground">
                          Documentos adjuntos ({seleccionado.documentosAdjuntos.length})
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {seleccionado.documentosAdjuntos.map((documento) => (
                            <Badge key={documento} variant="secondary">
                              {documento}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div>
                        <button
                          type="button"
                          onClick={() => setVerRelato((previo) => !previo)}
                          aria-expanded={verRelato}
                          className="flex items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
                        >
                          <ChevronDownIcon
                            className={cn('size-4 transition-transform', verRelato && 'rotate-180')}
                            aria-hidden
                          />
                          Relato clínico en texto libre
                        </button>
                        {verRelato && (
                          <p className="mt-2 max-h-72 overflow-y-auto rounded-lg bg-background p-3 text-sm whitespace-pre-wrap">
                            {seleccionado.texto}
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-full min-h-48 items-center justify-center">
                      <p className="max-w-[16rem] text-center text-sm text-muted-foreground">
                        Al elegir un informe aparecen aquí el paciente, la póliza y los documentos
                        adjuntos.
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
          </Card>
        </div>

        {/* Columna de resultado: ocupa el alto de la fila para no dejar hueco. */}
        <div className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertTitle>No se pudo completar la evaluación</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {avisos.map((aviso) => (
            <Alert key={aviso}>
              <AlertCircleIcon />
              <AlertTitle>Aviso</AlertTitle>
              <AlertDescription>{aviso}</AlertDescription>
            </Alert>
          ))}

          {!hayResultado && !error && (
            <Card className="flex-1">
              <CardContent className="flex h-full flex-col items-center justify-center gap-3 text-center">
                <span className="flex size-14 items-center justify-center rounded-2xl bg-accent">
                  <WandSparklesIcon className="size-6 text-accent-foreground" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="font-medium">
                    {codigo ? 'Listo para evaluar' : 'Elige un informe para empezar'}
                  </p>
                  <p className="max-w-xs text-sm text-muted-foreground">
                    {codigo
                      ? 'Pulsa «Evaluar» y aquí aparecerá el proceso paso a paso.'
                      : 'Cada informe recorre un camino distinto del motor de reglas.'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {(pasos.length > 0 || evaluando) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex flex-wrap items-center gap-2">
                  <FileTextIcon className="size-4 text-muted-foreground" aria-hidden />
                  Lo que está haciendo el agente
                  {cabecera && (
                    <span className="text-xs font-normal text-muted-foreground">
                      {cabecera.modelo} · esfuerzo {cabecera.esfuerzo} · datos de{' '}
                      {cabecera.origenDatos}
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <LineaTiempo pasos={pasos} activo={evaluando} />
              </CardContent>
            </Card>
          )}

          {/* Los chequeos aparecen en cuanto el motor de reglas responde, sin
              esperar a que el modelo termine de redactar los textos. */}
          {!dictamen && chequeos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  Verificaciones
                  {veredictoPreliminar && <VeredictoBadge veredicto={veredictoPreliminar} />}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ListaChequeos chequeos={chequeos} />
              </CardContent>
            </Card>
          )}

          {dictamen && <TarjetaDictamen dictamen={dictamen} msTotal={msTotal} />}
        </div>
      </div>
    </div>
  );
}

function Dato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{termino}</dt>
      <dd className="truncate">{valor}</dd>
    </div>
  );
}
