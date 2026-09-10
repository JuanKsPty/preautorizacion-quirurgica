import { dinero } from '@/lib/formato';
import { cn } from '@/lib/utils';
import type { Desglose } from '@/types/api';

/**
 * El reparto del costo, en el orden en que se aplica una poliza de gastos
 * medicos mayores: deducible, lo que el plan reconoce, coaseguro y tope.
 *
 * Se muestra el orden y no solo el total porque el total no se puede discutir
 * y cada tramo si. Todas las cifras vienen calculadas en el servidor en
 * centavos enteros; aqui no se hace aritmetica.
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

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <tbody className="divide-y">
          {filas.map((fila) => (
            <tr key={fila.concepto}>
              <td className="py-2 pr-4">{fila.concepto}</td>
              <td className="py-2 text-right tabular-nums whitespace-nowrap">
                {dinero(fila.valor)}
              </td>
              <td className="py-2 pl-3 text-right text-xs text-muted-foreground whitespace-nowrap">
                {fila.quien === 'paciente' ? 'paciente' : ''}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="border-t-2">
          <tr className="font-medium">
            <td className="py-2 pr-4">Cubre la aseguradora</td>
            <td className={cn('py-2 text-right tabular-nums whitespace-nowrap', 'text-exito')}>
              {dinero(desglose.cubierto_aseguradora)}
            </td>
            <td />
          </tr>
          <tr className="font-medium">
            <td className="py-2 pr-4">A cargo del paciente</td>
            <td className="py-2 text-right tabular-nums whitespace-nowrap">
              {dinero(desglose.a_cargo_paciente)}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
      <p className="mt-3 text-xs text-muted-foreground">
        Suma asegurada disponible tras esta cirugía:{' '}
        <span className="tabular-nums">{dinero(desglose.tope_disponible_despues)}</span>
      </p>
    </div>
  );
}
