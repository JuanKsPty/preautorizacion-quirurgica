import { useQuery } from '@tanstack/react-query';
import { BanIcon, SearchIcon } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { NOMBRE_PLAN, dinero } from '@/lib/formato';
import { cn } from '@/lib/utils';
import { listarPolizas, listarProcedimientos } from '@/services/catalogoService';
import type { NivelPlan } from '@/types/api';

const PLANES: NivelPlan[] = ['basico', 'preferente', 'ejecutivo'];

/**
 * El catalogo y las polizas, tal como los lee el motor de reglas.
 *
 * Esta pantalla existe para que el dictamen no haya que creerselo: quien lo
 * evalua puede comprobar aqui que la carencia, la cobertura, la exclusion y los
 * documentos exigidos son los que estaban publicados de antemano.
 */
export function ReglasPage() {
  const procedimientos = useQuery({
    queryKey: ['procedimientos'],
    queryFn: listarProcedimientos,
  });
  const polizas = useQuery({ queryKey: ['polizas'], queryFn: listarPolizas });

  const [buscarProcedimiento, setBuscarProcedimiento] = useState('');
  const [buscarPoliza, setBuscarPoliza] = useState('');

  const procedimientosFiltrados = useMemo(() => {
    const termino = buscarProcedimiento.trim().toLowerCase();
    if (!termino) return procedimientos.data ?? [];
    return (procedimientos.data ?? []).filter(
      (p) =>
        p.cpt.toLowerCase().includes(termino) ||
        p.nombre.toLowerCase().includes(termino) ||
        p.categoria.toLowerCase().includes(termino)
    );
  }, [procedimientos.data, buscarProcedimiento]);

  const polizasFiltradas = useMemo(() => {
    const termino = buscarPoliza.trim().toLowerCase();
    if (!termino) return polizas.data ?? [];
    return (polizas.data ?? []).filter(
      (p) => p.numero.toLowerCase().includes(termino) || p.titular.toLowerCase().includes(termino)
    );
  }, [polizas.data, buscarPoliza]);

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Catálogo y pólizas</h1>
        <p className="text-sm text-muted-foreground">
          Las condiciones que aplica el motor, publicadas de antemano.
        </p>
      </div>

      <Card>
        <CardHeader className="gap-3">
          <CardTitle className="text-base">
            Catálogo de procedimientos
            {procedimientos.data && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {procedimientosFiltrados.length} de {procedimientos.data.length} entradas
              </span>
            )}
          </CardTitle>
          {procedimientos.data && (
            <div className="relative max-w-sm">
              <SearchIcon
                className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Buscar por CPT, procedimiento o categoría…"
                value={buscarProcedimiento}
                onChange={(evento) => setBuscarProcedimiento(evento.target.value)}
                className="pl-8"
                aria-label="Buscar en el catálogo de procedimientos"
              />
            </div>
          )}
        </CardHeader>
        <CardContent>
          {procedimientos.isPending && <Skeleton className="h-64 w-full" />}
          {procedimientos.data && procedimientosFiltrados.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Ningún procedimiento coincide con «{buscarProcedimiento}».
            </p>
          )}
          {procedimientos.data && procedimientosFiltrados.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th rowSpan={2} className="pb-2 pr-4 align-bottom font-medium">
                      CPT
                    </th>
                    <th rowSpan={2} className="pb-2 pr-4 align-bottom font-medium">
                      Procedimiento
                    </th>
                    <th
                      colSpan={3}
                      className="border-b pb-1 pr-4 text-center font-medium whitespace-nowrap"
                    >
                      Carencia (días)
                    </th>
                    <th colSpan={3} className="border-b pb-1 pr-4 text-center font-medium">
                      Cobertura
                    </th>
                    <th rowSpan={2} className="pb-2 align-bottom font-medium">
                      Documentos exigidos
                    </th>
                  </tr>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    {PLANES.map((plan) => (
                      <th key={`carencia-${plan}`} className="pt-1 pb-2 pr-4 font-normal">
                        {NOMBRE_PLAN[plan]}
                      </th>
                    ))}
                    {PLANES.map((plan) => (
                      <th key={`cobertura-${plan}`} className="pt-1 pb-2 pr-4 font-normal">
                        {NOMBRE_PLAN[plan]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {procedimientosFiltrados.map((procedimiento) => (
                    <tr key={procedimiento.cpt}>
                      <td className="py-3 pr-4 align-top font-mono whitespace-nowrap">
                        {procedimiento.cpt}
                      </td>
                      <td className="py-3 pr-4 align-top">
                        <p className="font-medium">{procedimiento.nombre}</p>
                        <p className="text-xs text-muted-foreground">{procedimiento.categoria}</p>
                        {procedimiento.exclusion && (
                          <p className="mt-1 flex items-start gap-1.5 text-xs text-rechazo">
                            <BanIcon className="mt-0.5 size-3 shrink-0" aria-hidden />
                            Excluido: {procedimiento.exclusion}
                          </p>
                        )}
                      </td>
                      {PLANES.map((plan) => (
                        <td
                          key={`carencia-${plan}`}
                          className="py-3 pr-4 align-top tabular-nums whitespace-nowrap"
                        >
                          {procedimiento.carenciaDias[plan]}
                        </td>
                      ))}
                      {PLANES.map((plan) => (
                        <td
                          key={`cobertura-${plan}`}
                          className={cn(
                            'py-3 pr-4 align-top tabular-nums whitespace-nowrap',
                            procedimiento.coberturaPorcentaje[plan] === 0 && 'text-rechazo'
                          )}
                        >
                          {procedimiento.coberturaPorcentaje[plan]}%
                        </td>
                      ))}
                      <td className="py-3 align-top">
                        <div className="flex flex-wrap gap-1">
                          {procedimiento.documentosRequeridos.map((documento) => (
                            <Badge key={documento} variant="secondary" className="text-[11px]">
                              {documento}
                            </Badge>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="gap-3">
          <CardTitle className="text-base">
            Pólizas en el sistema
            {polizas.data && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {polizasFiltradas.length} de {polizas.data.length}
              </span>
            )}
          </CardTitle>
          {polizas.data && (
            <div className="relative max-w-sm">
              <SearchIcon
                className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Buscar por número de póliza o titular…"
                value={buscarPoliza}
                onChange={(evento) => setBuscarPoliza(evento.target.value)}
                className="pl-8"
                aria-label="Buscar en las pólizas"
              />
            </div>
          )}
        </CardHeader>
        <CardContent>
          {polizas.isPending && <Skeleton className="h-48 w-full" />}
          {polizas.data && polizasFiltradas.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Ninguna póliza coincide con «{buscarPoliza}».
            </p>
          )}
          {polizas.data && polizasFiltradas.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Póliza</th>
                    <th className="pb-2 pr-4 font-medium">Titular</th>
                    <th className="pb-2 pr-4 font-medium">Plan</th>
                    <th className="pb-2 pr-4 font-medium">Estado</th>
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Deducible</th>
                    <th className="pb-2 pr-4 font-medium">Coaseguro</th>
                    <th className="pb-2 font-medium whitespace-nowrap">Suma disponible</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {polizasFiltradas.map((poliza) => (
                    <tr key={poliza.numero}>
                      <td className="py-3 pr-4 font-mono whitespace-nowrap">{poliza.numero}</td>
                      <td className="py-3 pr-4">
                        <p>{poliza.titular}</p>
                        {poliza.preexistenciasDeclaradas.length > 0 && (
                          <p className="text-xs text-muted-foreground">
                            declara: {poliza.preexistenciasDeclaradas.join(', ')}
                          </p>
                        )}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">{NOMBRE_PLAN[poliza.plan]}</td>
                      <td className="py-3 pr-4">
                        <Badge
                          className={
                            poliza.estado === 'vigente'
                              ? 'bg-exito-fondo text-exito'
                              : 'bg-rechazo-fondo text-rechazo'
                          }
                        >
                          {poliza.estado === 'vigente' ? 'Vigente' : 'En mora'}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 tabular-nums whitespace-nowrap">
                        {dinero(poliza.deducibleAnual - poliza.deducibleConsumido)}
                      </td>
                      <td className="py-3 pr-4 tabular-nums">{poliza.coaseguroPorcentaje}%</td>
                      <td className="py-3 tabular-nums whitespace-nowrap">
                        {dinero(poliza.topeAnual - poliza.topeConsumido)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Precedencia entre reglas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>Si fallan varias condiciones a la vez, se cita siempre la primera de esta lista:</p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>Póliza no vigente, en mora o cancelada — se rechaza.</li>
            <li>Exclusión absoluta del procedimiento — se rechaza.</li>
            <li>El plan contratado no cubre el procedimiento — se rechaza.</li>
            <li>Carencia no cumplida y no es urgencia — se rechaza, indicando desde cuándo sí.</li>
            <li>Preexistencia no declarada — pasa a revisión médica humana.</li>
            <li>Faltan documentos exigidos — se pide la lista concreta.</li>
            <li>La suma asegurada no alcanza — se aprueba con condiciones.</li>
            <li>Todo conforme — se aprueba.</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
