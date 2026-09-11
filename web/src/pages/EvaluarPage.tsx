import { useQuery } from '@tanstack/react-query';
import {
  AlertCircleIcon,
  ChevronRightIcon,
  FileTextIcon,
  PaperclipIcon,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { usePreautorizacion } from '@/hooks/usePreautorizacion';
import { NOMBRE_PLAN, dinero, fecha, segundos } from '@/lib/formato';
import { listarInformes, listarPolizas } from '@/services/catalogoService';

export function EvaluarPage() {
  const [codigo, setCodigo] = useState('');
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
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Nueva solicitud</h1>
        <p className="text-sm text-muted-foreground">
          Elige un informe y mira cada paso del agente hasta el dictamen.
        </p>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(340px,400px)_1fr] lg:grid-rows-[minmax(0,1fr)]">
        {/* Columna de trabajo. */}
        <div className="flex min-h-0 flex-col">
          <Card className="flex min-h-0 flex-1">
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

              <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
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
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl bg-muted/50 p-4">
                  {seleccionado ? (
                    <div className="flex min-h-0 flex-1 flex-col gap-3">
                      {/* Nombre y etiqueta comparten fila y ninguno envuelve:
                          que el informe sea urgente no puede mover nada de lo
                          que viene debajo. */}
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">{seleccionado.paciente}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {seleccionado.hospital} · {seleccionado.medicoTratante}
                          </p>
                        </div>
                        {seleccionado.esEmergencia && (
                          <Badge className="shrink-0 bg-alerta-fondo text-alerta">
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

                      {/* En ventana aparte: desplegar la lista aqui moveria
                          todo lo que viene debajo. */}
                      <Dialog>
                        <DialogTrigger className="flex w-full shrink-0 items-center gap-1.5 rounded-lg bg-background px-3 py-2 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
                          <PaperclipIcon
                            className="size-4 shrink-0 text-muted-foreground"
                            aria-hidden
                          />
                          Documentos adjuntos ({seleccionado.documentosAdjuntos.length})
                          <ChevronRightIcon
                            className="ml-auto size-4 shrink-0 text-muted-foreground"
                            aria-hidden
                          />
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-md">
                          <DialogHeader>
                            <DialogTitle>Documentos adjuntos</DialogTitle>
                            <DialogDescription>
                              {seleccionado.documentosAdjuntos.length} documentos que el hospital
                              envió con el informe {seleccionado.codigo}.
                            </DialogDescription>
                          </DialogHeader>
                          <ul className="space-y-2">
                            {seleccionado.documentosAdjuntos.map((documento) => (
                              <li
                                key={documento}
                                className="flex items-center gap-2.5 rounded-lg bg-muted/50 px-3 py-2 text-sm"
                              >
                                <FileTextIcon
                                  className="size-4 shrink-0 text-muted-foreground"
                                  aria-hidden
                                />
                                {documento}
                              </li>
                            ))}
                          </ul>
                        </DialogContent>
                      </Dialog>

                      {/* El relato ocupa lo que sobre y hace scroll por dentro,
                          asi la tarjeta mide igual con todos los informes. */}
                      <div className="flex min-h-0 flex-1 flex-col gap-1.5">
                        <p className="text-xs text-muted-foreground">
                          Relato clínico en texto libre
                        </p>
                        {/* El padding no aparta la barra de scroll de su propio
                            borde (solo mueve el texto: la barra se pinta
                            igual, pegada al borde). Para separarla de verdad
                            hace falta que lo que hace scroll sea mas angosto
                            que la caja, con un carril en blanco al lado. */}
                        <div className="flex min-h-24 flex-1 rounded-lg bg-background">
                          <p className="scroll-fino min-w-0 flex-1 overflow-y-auto py-3 pr-2 pl-3 text-sm whitespace-pre-wrap">
                            {seleccionado.texto}
                          </p>
                          <div className="w-5 shrink-0" aria-hidden />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-1 items-center justify-center">
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
