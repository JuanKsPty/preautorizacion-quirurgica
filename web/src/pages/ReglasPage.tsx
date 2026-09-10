import { useQuery } from '@tanstack/react-query';
import { BanIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { NOMBRE_PLAN, dinero } from '@/lib/formato';
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reglas publicadas</h1>
        <p className="text-sm text-muted-foreground">
          Las condiciones que aplica el motor. Están aquí para que cualquier dictamen se pueda
          verificar contra la norma, en vez de tener que confiar en el resultado.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Catálogo de procedimientos
            {procedimientos.data && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {procedimientos.data.length} entradas
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {procedimientos.isPending && <Skeleton className="h-64 w-full" />}
          {procedimientos.data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">CPT</th>
                    <th className="pb-2 pr-4 font-medium">Procedimiento</th>
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Carencia (días)</th>
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Cobertura</th>
                    <th className="pb-2 font-medium">Documentos exigidos</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {procedimientos.data.map((procedimiento) => (
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
                      <td className="py-3 pr-4 align-top">
                        <ul className="space-y-0.5 text-xs tabular-nums">
                          {PLANES.map((plan) => (
                            <li key={plan}>
                              {NOMBRE_PLAN[plan]}: {procedimiento.carenciaDias[plan]}
                            </li>
                          ))}
                        </ul>
                      </td>
                      <td className="py-3 pr-4 align-top">
                        <ul className="space-y-0.5 text-xs tabular-nums">
                          {PLANES.map((plan) => (
                            <li
                              key={plan}
                              className={
                                procedimiento.coberturaPorcentaje[plan] === 0
                                  ? 'text-rechazo'
                                  : undefined
                              }
                            >
                              {NOMBRE_PLAN[plan]}: {procedimiento.coberturaPorcentaje[plan]}%
                            </li>
                          ))}
                        </ul>
                      </td>
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
        <CardHeader>
          <CardTitle className="text-base">Pólizas en el sistema</CardTitle>
        </CardHeader>
        <CardContent>
          {polizas.isPending && <Skeleton className="h-48 w-full" />}
          {polizas.data && (
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
                  {polizas.data.map((poliza) => (
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
          <p>
            Cuando fallan varias condiciones a la vez, el motivo que se le cita al asegurado es
            siempre el mismo, en este orden:
          </p>
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
          <p>
            El punto 5 va antes del 6 a propósito: pedirle papeles a un paciente cuyo caso irá a
            revisión de todos modos es mandarlo a una diligencia inútil. Y una urgencia exonera la
            carencia, porque si no el sistema rechazaría una apendicitis aguda.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
