import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircleIcon } from 'lucide-react';
import { useEffect } from 'react';
import type { SubmitHandler } from 'react-hook-form';
import { useForm } from 'react-hook-form';
import { useNavigate, useParams } from 'react-router';
import { toast } from 'sonner';
import { AvisoSoloLectura } from '@/components/expediente/AvisoSoloLectura';
import { BarraAcciones } from '@/components/formulario/BarraAcciones';
import { Campo } from '@/components/formulario/Campo';
import { CampoChips } from '@/components/formulario/CampoChips';
import { CampoSelect } from '@/components/formulario/CampoSelect';
import { SeccionFormulario } from '@/components/formulario/SeccionFormulario';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useEscrituraHabilitada } from '@/hooks/useEscrituraHabilitada';
import type { EntradaPoliza, SalidaPoliza } from '@/lib/esquemas/poliza';
import { esquemaPoliza } from '@/lib/esquemas/poliza';
import {
  ESTADO_POLIZA,
  NOMBRE_PLAN,
  dinero,
  dineroPlano,
  fechaInput,
  parseDinero,
} from '@/lib/formato';
import { actualizarPoliza, crearPoliza, obtenerPoliza } from '@/services/catalogoService';
import type { NivelPlan, PolizaEntradaDto } from '@/types/api';

const PLANES: NivelPlan[] = ['basico', 'preferente', 'ejecutivo'];
const ESTADOS = ['vigente', 'en_mora', 'vencida', 'cancelada'] as const;

const VACIA: EntradaPoliza = {
  numero: '',
  titular: '',
  cedula: '',
  plan: 'preferente',
  estado: 'vigente',
  inicio_vigencia: fechaInput(new Date()),
  fin_vigencia: '',
  deducible_anual: '0.00',
  deducible_consumido: '0.00',
  coaseguro_porcentaje: 20,
  tope_anual: '50000.00',
  tope_consumido: '0.00',
  red_preferente: true,
  preexistencias_declaradas: [],
  dependientes: [],
};

export function PolizaFormPage() {
  const { numero } = useParams();
  const esEdicion = numero !== undefined;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const escritura = useEscrituraHabilitada();

  const existente = useQuery({
    queryKey: ['poliza', numero],
    queryFn: () => obtenerPoliza(numero!),
    enabled: esEdicion,
  });

  // Los tres genericos son obligatorios: el dinero entra como texto y sale como
  // numero, asi que la entrada y la salida del esquema NO son el mismo tipo.
  const form = useForm<EntradaPoliza, unknown, SalidaPoliza>({
    resolver: zodResolver(esquemaPoliza),
    mode: 'onBlur',
    defaultValues: VACIA,
  });

  useEffect(() => {
    const p = existente.data;
    if (!p) return;
    form.reset({
      numero: p.numero,
      titular: p.titular,
      cedula: p.cedula,
      plan: p.plan,
      estado: p.estado,
      inicio_vigencia: fechaInput(p.inicioVigencia),
      fin_vigencia: fechaInput(p.finVigencia),
      deducible_anual: dineroPlano(p.deducibleAnual),
      deducible_consumido: dineroPlano(p.deducibleConsumido),
      coaseguro_porcentaje: p.coaseguroPorcentaje,
      tope_anual: dineroPlano(p.topeAnual),
      tope_consumido: dineroPlano(p.topeConsumido),
      red_preferente: p.redPreferente,
      preexistencias_declaradas: p.preexistenciasDeclaradas,
      dependientes: p.dependientes,
    });
  }, [existente.data, form]);

  const guardar = useMutation({
    mutationFn: (valores: SalidaPoliza) => {
      const { numero: escrito, ...resto } = valores;
      const cuerpo: PolizaEntradaDto = resto;
      return esEdicion
        ? actualizarPoliza(numero!, cuerpo)
        : crearPoliza(escrito ? { ...cuerpo, numero: escrito } : cuerpo);
    },
    onSuccess: async ({ registro, avisos }) => {
      // Obligatorio: la pantalla Evaluar lee estas claves con 30 s de frescura,
      // asi que sin invalidar la poliza nueva no seria seleccionable enseguida.
      await queryClient.invalidateQueries({ queryKey: ['polizas'] });
      avisos.forEach((aviso) => toast.warning(aviso));
      toast.success(`Póliza ${registro.numero} guardada`, {
        action: {
          label: 'Crear informe',
          onClick: () => navigate(`/expediente/informes/nuevo?poliza=${registro.numero}`),
        },
      });
      navigate('/expediente');
    },
    onError: (error: Error & { status?: number }) => {
      if (error.status === 409) {
        form.setError('numero', { message: 'Ya existe una póliza con ese número' });
        form.setFocus('numero');
      }
      toast.error(error.message);
    },
  });

  const enviar: SubmitHandler<SalidaPoliza> = (valores) => guardar.mutate(valores);
  const errores = form.formState.errors;
  const valores = form.watch();

  if (esEdicion && existente.isPending) {
    return <Skeleton className="h-96 w-full" />;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            {esEdicion ? 'Editar póliza' : 'Nueva póliza'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Los términos que el motor de reglas aplicará a cada solicitud de esta persona.
          </p>
        </div>
        {esEdicion && <span className="font-mono text-sm text-muted-foreground">{numero}</span>}
      </section>

      <AvisoSoloLectura estado={escritura} />

      {existente.isError && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>No se pudo cargar la póliza</AlertTitle>
          <AlertDescription>{(existente.error as Error).message}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-4" onSubmit={form.handleSubmit(enviar)} noValidate>
        <SeccionFormulario titulo="Identificación">
          <Campo
            id="numero"
            etiqueta="Número de póliza"
            error={errores.numero?.message}
            ayuda={esEdicion ? 'Es la clave en Notion y no se cambia.' : 'Si lo dejas vacío se genera solo.'}
          >
            <Input
              id="numero"
              className="font-mono"
              placeholder="POL-2026-0001"
              disabled={esEdicion}
              {...form.register('numero')}
            />
          </Campo>

          <Campo id="titular" etiqueta="Titular" error={errores.titular?.message}>
            <Input id="titular" {...form.register('titular')} />
          </Campo>

          <Campo id="cedula" etiqueta="Cédula" error={errores.cedula?.message}>
            <Input id="cedula" placeholder="8-812-2043" {...form.register('cedula')} />
          </Campo>

          <Campo id="plan" etiqueta="Plan contratado">
            <CampoSelect id="plan" {...form.register('plan')}>
              {PLANES.map((plan) => (
                <option key={plan} value={plan}>
                  {NOMBRE_PLAN[plan]}
                </option>
              ))}
            </CampoSelect>
          </Campo>

          <Campo
            id="estado"
            etiqueta="Estado"
            ayuda={
              <span className="inline-flex items-center gap-2">
                Así se verá:
                <Badge
                  className={
                    valores.estado === 'vigente'
                      ? 'bg-exito-fondo text-exito'
                      : 'bg-rechazo-fondo text-rechazo'
                  }
                >
                  {ESTADO_POLIZA[valores.estado] ?? valores.estado}
                </Badge>
              </span>
            }
          >
            <CampoSelect id="estado" {...form.register('estado')}>
              {ESTADOS.map((estado) => (
                <option key={estado} value={estado}>
                  {ESTADO_POLIZA[estado] ?? estado}
                </option>
              ))}
            </CampoSelect>
          </Campo>
        </SeccionFormulario>

        <SeccionFormulario titulo="Vigencia">
          <Campo id="inicio" etiqueta="Inicio de vigencia" error={errores.inicio_vigencia?.message}>
            <Input id="inicio" type="date" {...form.register('inicio_vigencia')} />
          </Campo>
          <Campo id="fin" etiqueta="Fin de vigencia" error={errores.fin_vigencia?.message}>
            <Input id="fin" type="date" {...form.register('fin_vigencia')} />
          </Campo>
        </SeccionFormulario>

        <SeccionFormulario
          titulo="Condiciones económicas"
          descripcion="El motor calcula el reparto del costo con estos cuatro números."
        >
          <CampoDinero
            id="deducible_anual"
            etiqueta="Deducible anual"
            registro={form.register('deducible_anual')}
            error={errores.deducible_anual?.message}
          />
          <CampoDinero
            id="deducible_consumido"
            etiqueta="Deducible ya consumido"
            registro={form.register('deducible_consumido')}
            error={errores.deducible_consumido?.message}
          />
          <CampoDinero
            id="tope_anual"
            etiqueta="Suma asegurada anual"
            registro={form.register('tope_anual')}
            error={errores.tope_anual?.message}
          />
          <CampoDinero
            id="tope_consumido"
            etiqueta="Suma ya consumida"
            registro={form.register('tope_consumido')}
            error={errores.tope_consumido?.message}
          />

          <Campo
            id="coaseguro"
            etiqueta="Coaseguro"
            error={errores.coaseguro_porcentaje?.message}
            // La cadena mas importante de esta pantalla. Sin ella, media docena
            // de personas meteran el porcentaje de COBERTURA y el dinero saldra
            // mal sin que nadie lo note.
            ayuda="Porcentaje que paga el ASEGURADO después del deducible. Lo habitual: 10-30 %."
          >
            <div className="relative w-32">
              <Input
                id="coaseguro"
                type="number"
                min={0}
                max={100}
                step={1}
                className="pr-7 text-right tabular-nums"
                {...form.register('coaseguro_porcentaje')}
              />
              <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                %
              </span>
            </div>
          </Campo>

          {/* Lo mismo que enseña la pantalla de Reglamento, para que las dos
              coincidan y se vea el efecto de lo que se acaba de teclear. */}
          <div className="sm:col-span-2">
            <div className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-muted/50 px-3 py-2 text-xs">
              <Disponible
                etiqueta="Deducible disponible"
                total={valores.deducible_anual}
                consumido={valores.deducible_consumido}
              />
              <Disponible
                etiqueta="Suma disponible"
                total={valores.tope_anual}
                consumido={valores.tope_consumido}
              />
            </div>
          </div>
        </SeccionFormulario>

        <SeccionFormulario titulo="Cobertura declarada">
          <Campo id="red" etiqueta="Red preferente">
            <label className="flex items-center gap-2 text-sm">
              <input
                id="red"
                type="checkbox"
                className="size-4 rounded accent-[var(--primary)]"
                {...form.register('red_preferente')}
              />
              Atención dentro de la red preferente
            </label>
          </Campo>

          <Campo
            id="preexistencias"
            etiqueta="Preexistencias declaradas"
            ayuda="Lo declarado está cubierto; lo que aparezca en un informe y no esté aquí va a revisión médica."
            className="sm:col-span-2"
          >
            <CampoChips
              valores={valores.preexistencias_declaradas}
              onChange={(v) => form.setValue('preexistencias_declaradas', v, { shouldDirty: true })}
              marcador="Hipertensión arterial esencial…"
            />
          </Campo>

          <Campo
            id="dependientes"
            etiqueta="Dependientes"
            error={errores.dependientes?.message}
            className="sm:col-span-2"
          >
            <CampoChips
              valores={valores.dependientes}
              onChange={(v) => form.setValue('dependientes', v, { shouldDirty: true })}
              marcador="Nombre del dependiente…"
            />
          </Campo>
        </SeccionFormulario>

        <BarraAcciones
          sucio={form.formState.isDirty}
          guardando={guardar.isPending}
          bloqueado={!escritura.habilitada}
          onCancelar={() => navigate('/expediente')}
          onGuardar={form.handleSubmit(enviar)}
        />
      </form>
    </div>
  );
}

/** Lo que queda de un tope, calculado sobre lo que hay escrito ahora mismo. */
function Disponible({
  etiqueta,
  total,
  consumido,
}: {
  etiqueta: string;
  total: string | number;
  consumido: string | number;
}) {
  const restante = Math.max(
    0,
    (parseDinero(String(total)) ?? 0) - (parseDinero(String(consumido)) ?? 0)
  );
  return (
    <span className="text-muted-foreground">
      {etiqueta}{' '}
      <span className="font-medium tabular-nums text-foreground">{dinero(restante)}</span>
    </span>
  );
}

/** Campo de dinero con el prefijo B/. y alineado a la derecha. */
function CampoDinero({
  id,
  etiqueta,
  registro,
  error,
}: {
  id: string;
  etiqueta: string;
  registro: ReturnType<ReturnType<typeof useForm<EntradaPoliza, unknown, SalidaPoliza>>['register']>;
  error?: string;
}) {
  return (
    <Campo id={id} etiqueta={etiqueta} error={error}>
      <div className="relative">
        <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-xs text-muted-foreground">
          B/.
        </span>
        <Input
          id={id}
          type="text"
          inputMode="decimal"
          className="pl-10 text-right tabular-nums"
          {...registro}
        />
      </div>
    </Campo>
  );
}
