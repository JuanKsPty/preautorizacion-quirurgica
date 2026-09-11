import { z } from 'zod';
import { cedulaPanama, dineroTexto, fechaISO, requerido } from './comunes';

export const esquemaPoliza = z
  .object({
    numero: z
      .string()
      .trim()
      .regex(/^POL-\d{4}-\d{4}$/, 'Usa el formato POL-2026-0001')
      .or(z.literal('')),
    titular: requerido('El titular'),
    cedula: cedulaPanama('La cédula'),
    plan: z.enum(['basico', 'preferente', 'ejecutivo']),
    // Los cuatro literales exactos. No es cosmetico: el backend los pasa tal
    // cual a un tipo cerrado, y un valor inventado tumbaria la lectura de TODAS
    // las polizas durante un minuto.
    estado: z.enum(['vigente', 'en_mora', 'vencida', 'cancelada']),
    inicio_vigencia: fechaISO,
    fin_vigencia: fechaISO,
    deducible_anual: dineroTexto('El deducible anual'),
    deducible_consumido: dineroTexto('El deducible consumido'),
    coaseguro_porcentaje: z.coerce
      .number()
      .int('Usa un porcentaje entero')
      .min(0, 'El coaseguro no puede ser menor que 0')
      .max(100, 'El coaseguro no puede pasar de 100'),
    tope_anual: dineroTexto('La suma asegurada anual'),
    tope_consumido: dineroTexto('La suma consumida'),
    red_preferente: z.boolean(),
    preexistencias_declaradas: z.array(z.string().trim().min(1)),
    dependientes: z.array(
      z
        .string()
        .trim()
        .min(1)
        // Notion guarda los dependientes separados por «;»: uno dentro de un
        // nombre lo partiria en dos la proxima vez que se lea.
        .refine((v) => !v.includes(';'), {
          message: 'No uses «;»: añade cada dependiente por separado',
        })
    ),
  })
  .refine((p) => p.fin_vigencia > p.inicio_vigencia, {
    message: 'El fin de vigencia tiene que ser posterior al inicio',
    path: ['fin_vigencia'],
  })
  .refine((p) => p.tope_anual > 0, {
    message: 'La suma asegurada tiene que ser mayor que 0',
    path: ['tope_anual'],
  })
  .refine((p) => p.deducible_consumido <= p.deducible_anual, {
    message: 'Lo consumido no puede superar el deducible anual',
    path: ['deducible_consumido'],
  })
  .refine((p) => p.tope_consumido <= p.tope_anual, {
    message: 'Lo consumido no puede superar la suma asegurada anual',
    path: ['tope_consumido'],
  });

/** Lo que teclea la persona (el dinero, texto). */
export type EntradaPoliza = z.input<typeof esquemaPoliza>;
/** Lo que se envia (el dinero, numero). */
export type SalidaPoliza = z.output<typeof esquemaPoliza>;
