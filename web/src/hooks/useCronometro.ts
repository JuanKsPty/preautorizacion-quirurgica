import { useEffect, useState } from 'react';

/**
 * Milisegundos transcurridos mientras `activo` sea cierto.
 *
 * El contraste entre estos segundos y las horas o dias que tarda el proceso
 * manual es el argumento del producto, asi que se enseña siempre que haya una
 * espera — igual que hace la pantalla de evaluacion.
 */
export function useCronometro(activo: boolean): number {
  const [ms, setMs] = useState(0);

  useEffect(() => {
    if (!activo) return;
    const arranque = performance.now();
    const reloj = window.setInterval(() => setMs(performance.now() - arranque), 100);
    return () => window.clearInterval(reloj);
  }, [activo]);

  return activo ? ms : 0;
}
