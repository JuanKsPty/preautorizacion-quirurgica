import { dinero } from '@/lib/formato';
import type { Desglose } from '@/types/api';

/**
 * El reparto del costo, en el orden en que se aplica una poliza de gastos
 * medicos mayores: deducible, lo que el plan reconoce, coaseguro y tope.
 *
 * La pregunta que de verdad hace quien lee esto es "¿cuánto paga cada quién?",
 * asi que ese numero lleva el peso visual: cifra grande y una barra de
 * proporcion, arriba del todo. El itemizado explica el porqué, pero es
 * secundario. Todas las cifras vienen calculadas en el servidor en centavos
 * enteros; aqui no se hace aritmetica.
 */
export function TablaDesglose({ desglose }: { desglose: Desglose }) {
  const filas: { concepto: string; valor: number; quien: 'paciente' | 'aseguradora' | null }[] = [
    { concepto: 'Monto cotizado por el hospital', valor: desglose.monto_cotizado, quien: null },
    { concepto: 'Deducible anual pendiente', valor: desglose.deducible_aplicado, quien: 'paciente' },
    {
      concepto: `No reconocido por el plan (cubre ${desglose.cobertura_porcentaje}%)`,
      valor: desglose.no_reconocido_por_plan,
      quien: 'paciente',
    },
    { concepto: 'Coaseguro del asegurado', valor: desglose.coaseguro_asegurado, quien: 'paciente' },
  ];

  if (desglose.excede_tope) {
    filas.push({
      concepto: 'Excede la suma asegurada disponible',
      valor: desglose.exceso_sobre_tope,
      quien: 'paciente',
    });
  }

  const total = desglose.cubierto_aseguradora + desglose.a_cargo_paciente;
  const porcentajeAseguradora = total > 0 ? (desglose.cubierto_aseguradora / total) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg bg-exito-fondo p-4">
          <p className="text-xs font-medium text-exito">Cubre la aseguradora</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-exito">
            {dinero(desglose.cubierto_aseguradora)}
          </p>
        </div>
        <div className="rounded-lg bg-muted p-4">
          <p className="text-xs font-medium text-muted-foreground">A cargo del paciente</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {dinero(desglose.a_cargo_paciente)}
          </p>
        </div>
      </div>

      <div
        className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={`La aseguradora cubre ${porcentajeAseguradora.toFixed(0)}% del monto cotizado; el paciente asume el resto`}
      >
        <div className="h-full bg-exito" style={{ width: `${porcentajeAseguradora}%` }} />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <tbody className="divide-y">
            {filas.map((fila) => (
              <tr key={fila.concepto} className="text-muted-foreground">
                <td className="py-2 pr-4">{fila.concepto}</td>
                <td className="py-2 text-right tabular-nums whitespace-nowrap">
                  {dinero(fila.valor)}
                </td>
                <td className="py-2 pl-3 text-right text-xs whitespace-nowrap">
                  {fila.quien === 'paciente' ? 'paciente' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        Suma asegurada disponible tras esta cirugía:{' '}
        <span className="tabular-nums">{dinero(desglose.tope_disponible_despues)}</span>
      </p>
    </div>
  );
}
