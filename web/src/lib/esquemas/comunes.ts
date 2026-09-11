import { z } from 'zod';
import { parseDinero } from '@/lib/formato';

/**
 * Piezas compartidas por los dos formularios.
 *
 * Los campos van en snake_case a proposito: el formulario produce directamente
 * la forma que habla la API, sin una capa de traduccion en medio. Es la misma
 * decision que ya se tomo con `Dictamen`, y por la misma razon — traducir a
 * camelCase para volver a traducir al enviar solo añade dos sitios donde
 * equivocarse.
 */

export const requerido = (etiqueta: string) =>
  z.string().trim().min(1, `${etiqueta} es obligatorio`);

/** AAAA-MM-DD: lo que produce <input type="date">. */
export const fechaISO = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Usa una fecha con el formato AAAA-MM-DD');

/** Cedula panamena: 8-812-2043, PE-123-456, N-20-1234. */
export const cedulaPanama = (etiqueta: string) =>
  requerido(etiqueta).regex(
    /^[0-9A-Za-z]{1,3}-\d{1,5}-\d{1,6}$/,
    'Formato de cédula, por ejemplo 8-812-2043'
  );

/**
 * El dinero entra como texto y sale como numero.
 *
 * No puede ser `type="number"`: pondria flechas, la rueda del raton cambiaria
 * el valor en un formulario que trata de dinero, y rechazaria «12,500.00»
 * pegado dejando el campo vacio sin explicar por que.
 */
export const dineroTexto = (etiqueta: string, minimo = 0) =>
  z
    .string()
    .trim()
    .min(1, `${etiqueta} es obligatorio`)
    .transform((valor, ctx) => {
      const numero = parseDinero(valor);
      if (numero === null || numero < minimo) {
        ctx.addIssue({ code: 'custom', message: `${etiqueta} no es una cantidad válida` });
        return z.NEVER;
      }
      return numero;
    });
