import { useQuery } from '@tanstack/react-query';
import { AlertCircleIcon, PlayIcon, RotateCcwIcon, SquareIcon, ZapIcon } from 'lucide-react';
import { useMemo, useState } from 'react';
import { LineaTiempo } from '@/components/dictamen/LineaTiempo';
import { ListaChequeos } from '@/components/dictamen/ListaChequeos';
import { TarjetaDictamen } from '@/components/dictamen/TarjetaDictamen';
import { VeredictoBadge } from '@/components/dictamen/VeredictoBadge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { usePreautorizacion } from '@/hooks/usePreautorizacion';
import { NOMBRE_PLAN, dinero, fecha, segundos } from '@/lib/formato';
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Evaluar una solicitud</h1>
        <p className="text-sm text-muted-foreground">
          Elige un informe médico. El agente lo lee, lo mapea al catálogo, aplica las condiciones
          de la póliza y emite el dictamen — y se puede ver cada paso mientras lo hace.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="space-y-2">
            <Label htmlFor="informe">Informe médico recibido del hospital</Label>
            {informes.isPending ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <select
                id="informe"
                value={codigo}
                disabled={evaluando}
                onChange={(evento) => {
                  setCodigo(evento.target.value);
                  reiniciar();
                }}
                className="h-10 w-full rounded-md border border-input bg-transparent px-3 text-sm disabled:opacity-50"
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
          </div>

          {informes.isError && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertTitle>No se pudieron cargar los informes</AlertTitle>
              <AlertDescription>
                {informes.error instanceof Error ? informes.error.message : 'Error desconocido'}
              </AlertDescription>
            </Alert>
          )}

          {seleccionado && (
            <div className="space-y-4 rounded-md border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{seleccionado.paciente}</p>
                  <p className="text-sm text-muted-foreground">
                    {seleccionado.hospital} · {seleccionado.medicoTratante}
                  </p>
                </div>
                {seleccionado.esEmergencia && (
                  <Badge className="bg-alerta-fondo text-alerta">
                    <ZapIcon className="size-3" /> Urgencia declarada
                  </Badge>
                )}
              </div>

              <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Dato termino="Cirugía propuesta" valor={fecha(seleccionado.fechaCirugiaPropuesta)} />
                <Dato termino="Monto cotizado" valor={dinero(seleccionado.montoCotizado)} />
                <Dato termino="Póliza" valor={seleccionado.numeroPoliza} />
                <Dato
                  termino="Plan contratado"
                  valor={poliza ? NOMBRE_PLAN[poliza.plan] : '—'}
                />
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
                  className="text-sm font-medium hover:text-foreground/80"
                >
                  Relato clínico en texto libre {verRelato ? '−' : '+'}
                </button>
                {verRelato && (
                  <p className="mt-2 max-h-72 overflow-y-auto rounded-md bg-muted/60 p-4 text-sm whitespace-pre-wrap">
                    {seleccionado.texto}
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={!codigo || evaluando} onClick={() => void evaluar(codigo)}>
              <PlayIcon /> Evaluar
            </Button>
            {evaluando && (
              <>
                <Button variant="outline" onClick={cancelar}>
                  <SquareIcon /> Detener
                </Button>
                <span className="text-sm tabular-nums text-muted-foreground">
                  {segundos(msTranscurridos)}
                </span>
              </>
            )}
            {dictamen && (
              <Button variant="ghost" onClick={reiniciar}>
                <RotateCcwIcon /> Limpiar
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

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

      {(pasos.length > 0 || evaluando) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-3 text-base">
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
            <CardTitle className="flex items-center gap-3 text-base">
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
  );
}

function Dato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{termino}</dt>
      <dd>{valor}</dd>
    </div>
  );
}
