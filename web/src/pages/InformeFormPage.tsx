import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircleIcon,
  ArrowRightIcon,
  CircleAlertIcon,
  Loader2Icon,
  RefreshCwIcon,
  SparklesIcon,
  SquareIcon,
  StethoscopeIcon,
  WandSparklesIcon,
} from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import type { SubmitHandler } from 'react-hook-form';
import { useForm } from 'react-hook-form';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { AvisoSoloLectura } from '@/components/expediente/AvisoSoloLectura';
import { BarraAcciones } from '@/components/formulario/BarraAcciones';
import { Campo } from '@/components/formulario/Campo';
import { CampoChips } from '@/components/formulario/CampoChips';
import { CampoSelect } from '@/components/formulario/CampoSelect';
import { SeccionFormulario } from '@/components/formulario/SeccionFormulario';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { useCronometro } from '@/hooks/useCronometro';
import { useEscrituraHabilitada } from '@/hooks/useEscrituraHabilitada';
import { ESCENARIOS_DEMO } from '@/lib/escenarios-demo';
import type { EntradaInforme, SalidaInforme } from '@/lib/esquemas/informe';
import { esquemaInformeCon } from '@/lib/esquemas/informe';
import { NOMBRE_PLAN, dineroPlano, fechaInput, segundos } from '@/lib/formato';
import type { Origen } from '@/lib/origen';
import { clasesOrigen } from '@/lib/origen';
import { cn } from '@/lib/utils';
import {
  actualizarInforme,
  crearInforme,
  listarInformes,
  listarPolizas,
  listarProcedimientos,
  obtenerInforme,
} from '@/services/catalogoService';
import { extraerInforme } from '@/services/extraccionService';
import type { CampoInforme, InformeEntradaDto } from '@/types/api';

type CampoFormulario = keyof EntradaInforme;

const ETIQUETA: Record<string, string> = {
  paciente: 'Paciente',
  cedula: 'Cédula',
  numero_poliza: 'Póliza',
  hospital: 'Hospital',
  medico_tratante: 'Médico tratante',
  especialidad: 'Especialidad',
  fecha_informe: 'Fecha del informe',
  fecha_cirugia_propuesta: 'Fecha de cirugía',
  monto_cotizado: 'Monto cotizado',
};

const VACIO: EntradaInforme = {
  codigo: '',
  paciente: '',
  cedula: '',
  numero_poliza: '',
  hospital: '',
  medico_tratante: '',
  especialidad: '',
  fecha_informe: fechaInput(new Date()),
  fecha_cirugia_propuesta: '',
  es_emergencia: false,
  monto_cotizado: '',
  documentos_adjuntos: [],
  texto: '',
};

export function InformeFormPage() {
  const { codigo } = useParams();
  const [params] = useSearchParams();
  const esEdicion = codigo !== undefined;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const escritura = useEscrituraHabilitada();

  const polizas = useQuery({ queryKey: ['polizas'], queryFn: listarPolizas });
  const procedimientos = useQuery({
    queryKey: ['procedimientos'],
    queryFn: listarProcedimientos,
  });
  const informes = useQuery({ queryKey: ['informes'], queryFn: listarInformes });
  const existente = useQuery({
    queryKey: ['informe', codigo],
    queryFn: () => obtenerInforme(codigo!),
    enabled: esEdicion,
  });

  const [origen, setOrigen] = useState<Partial<Record<CampoFormulario, Origen>>>({});
  const [extraido, setExtraido] = useState<{
    diagnostico: string | null;
    cie10: string | null;
    cpt: string | null;
    ms: number;
    campos: number;
  } | null>(null);
  const [errorExtraccion, setErrorExtraccion] = useState<string | null>(null);
  const [polizaPropuesta, setPolizaPropuesta] = useState<string | null>(null);
  const textoExtraidoRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);

  const numerosPoliza = useMemo(
    () => (polizas.data ?? []).map((p) => p.numero),
    [polizas.data]
  );
  const documentosSugeridos = useMemo(
    () =>
      [
        ...new Set((procedimientos.data ?? []).flatMap((p) => p.documentosRequeridos)),
      ].sort(),
    [procedimientos.data]
  );

  const form = useForm<EntradaInforme, unknown, SalidaInforme>({
    resolver: zodResolver(esquemaInformeCon(numerosPoliza)),
    mode: 'onBlur',
    defaultValues: {
      ...VACIO,
      numero_poliza: params.get('poliza') ?? '',
    },
  });

  // Cargar el existente al editar.
  const cargadoRef = useRef(false);
  if (existente.data && !cargadoRef.current) {
    cargadoRef.current = true;
    const i = existente.data;
    form.reset({
      codigo: i.codigo,
      paciente: i.paciente,
      cedula: i.cedula,
      numero_poliza: i.numeroPoliza,
      hospital: i.hospital,
      medico_tratante: i.medicoTratante,
      especialidad: i.especialidad,
      fecha_informe: fechaInput(i.fechaInforme),
      fecha_cirugia_propuesta: fechaInput(i.fechaCirugiaPropuesta),
      es_emergencia: i.esEmergencia,
      monto_cotizado: dineroPlano(i.montoCotizado),
      documentos_adjuntos: i.documentosAdjuntos,
      texto: i.texto,
    });
    textoExtraidoRef.current = i.texto;
  }

  const valores = form.watch();
  const errores = form.formState.errors;
  const textoCambio = valores.texto !== textoExtraidoRef.current && extraido !== null;

  // ---------------------------------------------------------------- extraer

  const extraccion = useMutation({
    mutationFn: async (texto: string) => {
      const controlador = new AbortController();
      abortRef.current = controlador;
      return extraerInforme(texto, controlador.signal);
    },
    onSuccess: (respuesta) => {
      const marcas: Partial<Record<CampoFormulario, Origen>> = {};
      let rellenados = 0;

      const poner = (campo: CampoFormulario, valor: string | boolean | string[] | null) => {
        if (valor === null || valor === '' || (Array.isArray(valor) && valor.length === 0)) return;
        // Nunca se pisa un campo que la persona ya reviso: solo los que siguen
        // marcados como propuestos por el agente, o los que estan vacios.
        const actual = form.getValues(campo);
        if (origen[campo] === 'usuario' && actual) return;
        form.setValue(campo, valor as never, { shouldDirty: true });
        marcas[campo] = 'ia';
        rellenados += 1;
      };

      const c = respuesta.campos;
      poner('paciente', c.paciente);
      poner('cedula', c.cedula);
      poner('hospital', c.hospital);
      poner('medico_tratante', c.medico_tratante);
      poner('especialidad', c.especialidad);
      poner('fecha_informe', c.fecha_informe);
      poner('fecha_cirugia_propuesta', c.fecha_cirugia_propuesta);
      poner('es_emergencia', c.es_emergencia);
      poner('monto_cotizado', c.monto_cotizado === null ? null : dineroPlano(c.monto_cotizado));
      poner('documentos_adjuntos', c.documentos_adjuntos);

      // La póliza solo se acepta si existe: si no, el informe se guardaría pero
      // fallaría al evaluarse, que es mucho más tarde y mucho más confuso.
      if (c.numero_poliza) {
        if (numerosPoliza.includes(c.numero_poliza)) {
          poner('numero_poliza', c.numero_poliza);
          setPolizaPropuesta(null);
        } else {
          setPolizaPropuesta(c.numero_poliza);
        }
      }

      respuesta.campos_no_encontrados.forEach((campo: CampoInforme) => {
        if (!marcas[campo as CampoFormulario]) marcas[campo as CampoFormulario] = 'faltante';
      });

      setOrigen((previo) => ({ ...previo, ...marcas }));
      setExtraido({
        diagnostico: c.diagnostico_presuntivo,
        cie10: c.cie10_presuntivo,
        cpt: c.cpt_sugerido,
        ms: respuesta.ms,
        campos: rellenados,
      });
      setErrorExtraccion(null);
      textoExtraidoRef.current = valores.texto;

      if (respuesta.aviso) toast.warning(respuesta.aviso);
      else toast.success(`Se rellenaron ${rellenados} campos. Revísalos antes de guardar.`);
    },
    onError: (error: Error) => {
      if (abortRef.current?.signal.aborted) return;
      setErrorExtraccion(error.message);
    },
    onSettled: () => {
      abortRef.current = null;
    },
  });

  const msExtraccion = useCronometro(extraccion.isPending);

  /** Revisar un campo ES aceptarlo: la marca se borra en cuanto se toca. */
  const alTocar = (campo: CampoFormulario) => {
    if (origen[campo] && origen[campo] !== 'usuario') {
      setOrigen((previo) => ({ ...previo, [campo]: 'usuario' }));
    }
  };

  // ---------------------------------------------------------------- guardar

  const guardar = useMutation({
    mutationFn: (valores: SalidaInforme) => {
      const { codigo: escrito, ...resto } = valores;
      const cuerpo: InformeEntradaDto = resto;
      return esEdicion
        ? actualizarInforme(codigo!, cuerpo)
        : crearInforme(escrito ? { ...cuerpo, codigo: escrito } : cuerpo);
    },
    onSuccess: async ({ registro, avisos }, _v, contexto) => {
      await queryClient.invalidateQueries({ queryKey: ['informes'] });
      avisos.forEach((aviso) => toast.warning(aviso));
      if (contexto === 'evaluar') {
        navigate(`/evaluar?informe=${registro.codigo}`);
        return;
      }
      toast.success(`Informe ${registro.codigo} guardado`, {
        action: {
          label: 'Evaluar',
          onClick: () => navigate(`/evaluar?informe=${registro.codigo}`),
        },
      });
      navigate('/expediente');
    },
    onError: (error: Error & { status?: number }) => {
      if (error.status === 409) {
        form.setError('codigo', { message: 'Ya existe un informe con ese código' });
        form.setFocus('codigo');
      }
      toast.error(error.message);
    },
  });

  const enviar: SubmitHandler<SalidaInforme> = (v) => guardar.mutate(v);
  const enviarYEvaluar: SubmitHandler<SalidaInforme> = (v) =>
    guardar.mutate(v, { context: 'evaluar' } as never);

  const escenario = codigo ? ESCENARIOS_DEMO[codigo] : undefined;
  const faltantes = (Object.keys(origen) as CampoFormulario[]).filter(
    (campo) => origen[campo] === 'faltante'
  );

  if (esEdicion && existente.isPending) return <Skeleton className="h-96 w-full" />;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            {esEdicion ? 'Editar informe' : 'Nuevo informe médico'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Pega el informe tal como llegó del hospital y deja que el agente lo ordene.
          </p>
        </div>
        {esEdicion && <span className="font-mono text-sm text-muted-foreground">{codigo}</span>}
      </section>

      <AvisoSoloLectura estado={escritura} />

      {escenario && (
        <Alert>
          <CircleAlertIcon />
          <AlertTitle>Este informe sostiene un caso de la demostración</AlertTitle>
          <AlertDescription>
            Es el escenario de <strong>{escenario}</strong>. Si lo cambias, el README deja de
            coincidir con lo que hace la aplicación.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        {/* Fuente a la izquierda, resultado a la derecha: el orden en que se lee. */}
        <Card className="flex min-h-0 flex-col">
          <CardHeader>
            <CardTitle className="text-base">Informe recibido del hospital</CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
            <Textarea
              className="min-h-80 flex-1 resize-none"
              placeholder="Pega aquí el informe tal como llegó: el correo del hospital, el PDF copiado, el mensaje del médico…"
              disabled={extraccion.isPending}
              {...form.register('texto', { onChange: () => alTocar('texto') })}
            />
            {errores.texto && <p className="text-xs text-rechazo">{errores.texto.message}</p>}

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs tabular-nums text-muted-foreground">
                {valores.texto.length} caracteres
              </span>
              <div className="ml-auto flex gap-2">
                {extraccion.isPending && (
                  <>
                    <span className="self-center text-sm tabular-nums text-muted-foreground">
                      {segundos(msExtraccion)}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => abortRef.current?.abort()}
                    >
                      <SquareIcon /> Detener
                    </Button>
                  </>
                )}
                <Button
                  type="button"
                  disabled={valores.texto.trim().length < 120 || extraccion.isPending}
                  onClick={() => extraccion.mutate(valores.texto)}
                >
                  {extraccion.isPending ? (
                    <Loader2Icon className="animate-spin" />
                  ) : textoCambio ? (
                    <RefreshCwIcon />
                  ) : (
                    <WandSparklesIcon />
                  )}
                  {textoCambio ? 'Volver a extraer' : 'Extraer datos'}
                </Button>
              </div>
            </div>

            {textoCambio && (
              <p className="text-xs text-muted-foreground">
                El texto cambió desde la última lectura. Los campos que ya revisaste no se
                tocarán.
              </p>
            )}

            {errorExtraccion && (
              <Alert variant="destructive">
                <AlertCircleIcon />
                <AlertTitle>No se pudo leer el informe</AlertTitle>
                <AlertDescription className="space-y-2">
                  <p>{errorExtraccion}</p>
                  <p>Puedes escribir los datos a mano igualmente.</p>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
          {faltantes.length > 0 && (
            <Alert>
              <CircleAlertIcon />
              <AlertTitle>
                Faltan {faltantes.length} datos que el informe no menciona
              </AlertTitle>
              <AlertDescription>
                {/* No son errores de validacion todavia: gritar antes de que la
                    persona haya tenido ocasion de rellenarlos seria hostil. */}
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {faltantes.map((campo) => (
                    <button
                      key={campo}
                      type="button"
                      onClick={() => form.setFocus(campo)}
                      className="text-primary underline-offset-4 hover:underline"
                    >
                      {ETIQUETA[campo] ?? campo}
                    </button>
                  ))}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {extraido && (
            <>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-accent/50 px-3 py-2 text-sm">
                <SparklesIcon className="size-4 shrink-0 text-accent-foreground" aria-hidden />
                <span>
                  El agente rellenó{' '}
                  <strong className="tabular-nums">{extraido.campos}</strong> campos en{' '}
                  {segundos(extraido.ms)}. Revísalos antes de guardar.
                </span>
              </div>

              {(extraido.diagnostico || extraido.cie10 || extraido.cpt) && (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                  <StethoscopeIcon className="size-4 shrink-0" aria-hidden />
                  {extraido.diagnostico && (
                    <span>
                      El agente leyó:{' '}
                      <strong className="text-foreground">{extraido.diagnostico}</strong>
                    </span>
                  )}
                  {extraido.cie10 && <span className="font-mono">CIE-10 {extraido.cie10}</span>}
                  {extraido.cpt && <span className="font-mono">CPT {extraido.cpt}</span>}
                  {/* Estos tres no son campos del informe: el dictamen los vuelve
                      a deducir al evaluar. Decirlo evita que alguien los busque. */}
                  <span className="ml-auto">No se guardan: el dictamen los vuelve a deducir.</span>
                </div>
              )}
            </>
          )}

          <SeccionFormulario titulo="Identificación">
            <Campo
              id="codigo"
              etiqueta="Código"
              error={errores.codigo?.message}
              ayuda={esEdicion ? 'Es la clave en Notion y no se cambia.' : 'Si lo dejas vacío se genera solo.'}
            >
              <Input
                id="codigo"
                className="font-mono"
                placeholder="INF-2026-0001"
                disabled={esEdicion}
                {...form.register('codigo')}
              />
            </Campo>

            <Campo
              id="numero_poliza"
              etiqueta="Póliza"
              origen={origen.numero_poliza}
              error={errores.numero_poliza?.message}
              ayuda={
                polizaPropuesta ? (
                  <span className="text-alerta">
                    El informe cita la póliza{' '}
                    <span className="font-mono">{polizaPropuesta}</span>, que no existe.
                    Elige una de la lista o créala primero.
                  </span>
                ) : undefined
              }
            >
              <CampoSelect
                id="numero_poliza"
                className={clasesOrigen(origen.numero_poliza)}
                {...form.register('numero_poliza', { onChange: () => alTocar('numero_poliza') })}
              >
                <option value="">Selecciona una póliza…</option>
                {(polizas.data ?? []).map((p) => (
                  <option key={p.numero} value={p.numero}>
                    {p.numero} — {p.titular} — {NOMBRE_PLAN[p.plan]}
                  </option>
                ))}
              </CampoSelect>
            </Campo>

            <Campo
              id="paciente"
              etiqueta="Paciente"
              origen={origen.paciente}
              error={errores.paciente?.message}
            >
              <Input
                id="paciente"
                className={clasesOrigen(origen.paciente)}
                {...form.register('paciente', { onChange: () => alTocar('paciente') })}
              />
            </Campo>

            <Campo
              id="cedula"
              etiqueta="Cédula"
              origen={origen.cedula}
              error={errores.cedula?.message}
            >
              <Input
                id="cedula"
                className={clasesOrigen(origen.cedula)}
                placeholder="8-812-2043"
                {...form.register('cedula', { onChange: () => alTocar('cedula') })}
              />
            </Campo>
          </SeccionFormulario>

          <SeccionFormulario titulo="Atención">
            <Campo
              id="hospital"
              etiqueta="Hospital"
              origen={origen.hospital}
              error={errores.hospital?.message}
            >
              <Input
                id="hospital"
                list="hospitales"
                className={clasesOrigen(origen.hospital)}
                {...form.register('hospital', { onChange: () => alTocar('hospital') })}
              />
              <datalist id="hospitales">
                {[...new Set((informes.data ?? []).map((i) => i.hospital))].map((h) => (
                  <option key={h} value={h} />
                ))}
              </datalist>
            </Campo>

            <Campo
              id="medico"
              etiqueta="Médico tratante"
              origen={origen.medico_tratante}
              error={errores.medico_tratante?.message}
            >
              <Input
                id="medico"
                className={clasesOrigen(origen.medico_tratante)}
                {...form.register('medico_tratante', {
                  onChange: () => alTocar('medico_tratante'),
                })}
              />
            </Campo>

            <Campo
              id="especialidad"
              etiqueta="Especialidad"
              origen={origen.especialidad}
              error={errores.especialidad?.message}
            >
              <Input
                id="especialidad"
                list="especialidades"
                className={clasesOrigen(origen.especialidad)}
                {...form.register('especialidad', { onChange: () => alTocar('especialidad') })}
              />
              <datalist id="especialidades">
                {[...new Set((informes.data ?? []).map((i) => i.especialidad))].map((e) => (
                  <option key={e} value={e} />
                ))}
              </datalist>
            </Campo>

            <Campo
              id="monto"
              etiqueta="Monto cotizado"
              origen={origen.monto_cotizado}
              error={errores.monto_cotizado?.message}
            >
              <div className="relative">
                <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-xs text-muted-foreground">
                  B/.
                </span>
                <Input
                  id="monto"
                  inputMode="decimal"
                  className={cn('pl-10 text-right tabular-nums', clasesOrigen(origen.monto_cotizado))}
                  {...form.register('monto_cotizado', { onChange: () => alTocar('monto_cotizado') })}
                />
              </div>
            </Campo>

            <Campo
              id="fecha_informe"
              etiqueta="Fecha del informe"
              origen={origen.fecha_informe}
              error={errores.fecha_informe?.message}
            >
              <Input
                id="fecha_informe"
                type="date"
                className={clasesOrigen(origen.fecha_informe)}
                {...form.register('fecha_informe', { onChange: () => alTocar('fecha_informe') })}
              />
            </Campo>

            <Campo
              id="fecha_cirugia"
              etiqueta="Fecha propuesta de cirugía"
              origen={origen.fecha_cirugia_propuesta}
              error={errores.fecha_cirugia_propuesta?.message}
            >
              <Input
                id="fecha_cirugia"
                type="date"
                className={clasesOrigen(origen.fecha_cirugia_propuesta)}
                {...form.register('fecha_cirugia_propuesta', {
                  onChange: () => alTocar('fecha_cirugia_propuesta'),
                })}
              />
            </Campo>

            <Campo
              id="emergencia"
              etiqueta="Urgencia"
              className="sm:col-span-2"
              // Decirlo aqui importa: es la excepcion que cambia el veredicto.
              ayuda="Una urgencia exonera el periodo de carencia."
            >
              <label className="flex items-center gap-2 text-sm">
                <input
                  id="emergencia"
                  type="checkbox"
                  className="size-4 rounded accent-[var(--primary)]"
                  {...form.register('es_emergencia')}
                />
                El hospital lo declara como atención de urgencia
              </label>
            </Campo>
          </SeccionFormulario>

          <SeccionFormulario
            titulo="Documentos adjuntos"
            descripcion="El motor compara estos nombres con los que exige el procedimiento, así que usa los del catálogo."
          >
            <div className="sm:col-span-2">
              <CampoChips
                valores={valores.documentos_adjuntos}
                onChange={(v) => {
                  form.setValue('documentos_adjuntos', v, { shouldDirty: true });
                  alTocar('documentos_adjuntos');
                }}
                sugerencias={documentosSugeridos}
                marcador="Nombre del documento…"
              />
            </div>
          </SeccionFormulario>
        </div>
      </div>

      <BarraAcciones
        sucio={form.formState.isDirty}
        guardando={guardar.isPending}
        bloqueado={!escritura.habilitada}
        onCancelar={() => navigate('/expediente')}
        onGuardar={form.handleSubmit(enviar)}
        extra={
          <Button
            type="button"
            size="lg"
            disabled={!escritura.habilitada || guardar.isPending}
            onClick={form.handleSubmit(enviarYEvaluar)}
          >
            Guardar y evaluar <ArrowRightIcon />
          </Button>
        }
      />
    </div>
  );
}
