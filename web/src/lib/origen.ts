/**
 * De donde salio el valor de un campo del formulario.
 *
 * Se marca en pantalla con icono Y color Y texto, nunca solo con color: es la
 * regla del proyecto, y aqui ademas importa, porque distinguir «lo propuso el
 * agente» de «lo escribi yo» es justo lo que hace falta para revisar rapido.
 *
 * La marca se borra sola al primer cambio del campo: revisar un valor ES
 * editarlo o aceptarlo, asi que eso deja a la vista lo que todavia no se ha
 * mirado, sin ninguna interfaz extra.
 */
export type Origen = 'ia' | 'usuario' | 'faltante';

/** El lavado de «esto lo puso el agente». Hue 195: ningun veredicto lo usa. */
export function clasesOrigen(origen?: Origen): string {
  if (origen === 'ia') return 'border-primary/40 bg-accent/40';
  if (origen === 'faltante') return 'border-alerta/40';
  return '';
}
