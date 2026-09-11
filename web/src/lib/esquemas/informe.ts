import { z } from 'zod';
import { cedulaPanama, dineroTexto, fechaISO, requerido } from './comunes';

export const esquemaInforme = z
  .object({
    codigo: z
      .string()
      .trim()
      .regex(/^INF-\d{4}-\d{4}$/, 'Usa el formato INF-2026-0001')
      .or(z.literal('')),
    paciente: requerido('El paciente'),
    cedula: cedulaPanama('La cédula'),
    numero_poliza: requerido('La póliza'),
    hospital: requerido('El hospital'),
    medico_tratante: requerido('El médico tratante'),
    especialidad: requerido('La especialidad'),
    fecha_informe: fechaISO,
    fecha_cirugia_propuesta: fechaISO,
    es_emergencia: z.boolean(),
    monto_cotizado: dineroTexto('El monto cotizado', 0.01),
    documentos_adjuntos: z.array(z.string().trim().min(1)),
    // Por debajo de esto el emparejador no puede identificar el procedimiento,
    // asi que seria un informe imposible de evaluar.
    texto: z
      .string()
      .trim()
      .min(120, 'El relato clínico es demasiado corto para poder evaluarlo'),
  })
  .refine((i) => i.fecha_cirugia_propuesta >= i.fecha_informe, {
    message: 'La cirugía no puede ser anterior al informe',
    path: ['fecha_cirugia_propuesta'],
  });

/**
 * La poliza tiene que existir: TODA la evaluacion cuelga de que `numero_poliza`
 * case con una poliza real, asi que un texto libre aqui produce informes que
 * fallan al evaluarse, no al guardarse.
 */
export function esquemaInformeCon(polizasConocidas: readonly string[]) {
  return esquemaInforme.refine(
    (i) => polizasConocidas.length === 0 || polizasConocidas.includes(i.numero_poliza),
    { message: 'Esa póliza no existe en el sistema', path: ['numero_poliza'] }
  );
}

export type EntradaInforme = z.input<typeof esquemaInforme>;
export type SalidaInforme = z.output<typeof esquemaInforme>;
