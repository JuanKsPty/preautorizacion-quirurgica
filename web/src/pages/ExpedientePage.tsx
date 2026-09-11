import { useQuery } from '@tanstack/react-query';
import { DatabaseIcon, PencilIcon, PlusIcon } from 'lucide-react';
import { Link } from 'react-router';
import { BotonEscritura } from '@/components/expediente/BotonEscritura';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useEscrituraHabilitada } from '@/hooks/useEscrituraHabilitada';
import { ESTADO_POLIZA, NOMBRE_PLAN, dinero, fecha } from '@/lib/formato';
import { listarInformes, listarPolizas } from '@/services/catalogoService';

export function ExpedientePage() {
  const escritura = useEscrituraHabilitada();
  const polizas = useQuery({ queryKey: ['polizas'], queryFn: listarPolizas });
  const informes = useQuery({ queryKey: ['informes'], queryFn: listarInformes });

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Expediente</h1>
          <p className="text-sm text-muted-foreground">
            Las pólizas de la aseguradora y los informes que envía el hospital. Se guardan
            en Notion.
          </p>
        </div>
        {!escritura.habilitada && !escritura.cargando && (
          <Badge className="bg-alerta-fondo text-alerta">
            <DatabaseIcon /> Solo lectura
          </Badge>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Informes médicos
            {informes.data && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {informes.data.length}
              </span>
            )}
          </CardTitle>
          <CardAction>
            <BotonEscritura estado={escritura} a="/expediente/informes/nuevo">
              <PlusIcon /> Nuevo informe
            </BotonEscritura>
          </CardAction>
        </CardHeader>
        <CardContent>
          {informes.isPending && <Skeleton className="h-48 w-full" />}
          {informes.data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Código</th>
                    <th className="pb-2 pr-4 font-medium">Paciente</th>
                    <th className="pb-2 pr-4 font-medium">Hospital</th>
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Cirugía</th>
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Monto</th>
                    <th className="pb-2 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {informes.data.map((informe) => (
                    <tr key={informe.codigo}>
                      <td className="py-3 pr-4 font-mono whitespace-nowrap">
                        {informe.codigo}
                      </td>
                      <td className="py-3 pr-4">
                        {informe.paciente}
                        {informe.esEmergencia && (
                          <Badge className="ml-2 bg-alerta-fondo text-alerta">urgencia</Badge>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">{informe.hospital}</td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        {fecha(informe.fechaCirugiaPropuesta)}
                      </td>
                      <td className="py-3 pr-4 tabular-nums whitespace-nowrap">
                        {dinero(informe.montoCotizado)}
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/evaluar?informe=${informe.codigo}`}>Evaluar</Link>
                        </Button>
                        <BotonEscritura
                          estado={escritura}
                          a={`/expediente/informes/${informe.codigo}`}
                          variante="ghost"
                          tamano="sm"
                        >
                          <PencilIcon />
                        </BotonEscritura>
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
          <CardTitle className="text-base">
            Pólizas
            {polizas.data && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {polizas.data.length}
              </span>
            )}
          </CardTitle>
          <CardAction>
            <BotonEscritura estado={escritura} a="/expediente/polizas/nueva">
              <PlusIcon /> Nueva póliza
            </BotonEscritura>
          </CardAction>
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
                    <th className="pb-2 pr-4 font-medium whitespace-nowrap">Suma disponible</th>
                    <th className="pb-2 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {polizas.data.map((poliza) => (
                    <tr key={poliza.numero}>
                      <td className="py-3 pr-4 font-mono whitespace-nowrap">{poliza.numero}</td>
                      <td className="py-3 pr-4">{poliza.titular}</td>
                      <td className="py-3 pr-4 whitespace-nowrap">{NOMBRE_PLAN[poliza.plan]}</td>
                      <td className="py-3 pr-4">
                        <Badge
                          className={
                            poliza.estado === 'vigente'
                              ? 'bg-exito-fondo text-exito'
                              : 'bg-rechazo-fondo text-rechazo'
                          }
                        >
                          {ESTADO_POLIZA[poliza.estado] ?? poliza.estado}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 tabular-nums whitespace-nowrap">
                        {dinero(poliza.topeAnual - poliza.topeConsumido)}
                      </td>
                      <td className="py-3 text-right">
                        <BotonEscritura
                          estado={escritura}
                          a={`/expediente/polizas/${poliza.numero}`}
                          variante="ghost"
                          tamano="sm"
                        >
                          <PencilIcon />
                        </BotonEscritura>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
