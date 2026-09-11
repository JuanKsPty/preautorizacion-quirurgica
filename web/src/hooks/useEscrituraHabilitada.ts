import { useQuery, useQueryClient } from '@tanstack/react-query';
import { demoModeEnabled } from '@/lib/demo-data';
import { getHealth } from '@/services/systemService';

export interface EstadoEscritura {
  habilitada: boolean;
  /** Frase en español lista para mostrar. `null` mientras se consulta. */
  motivo: string | null;
  /** Detalle técnico de Notion, si lo hay. Va aparte, en monoespaciada. */
  detalle: string | null;
  cargando: boolean;
  reintentar: () => void;
}

/**
 * Si se puede crear y editar, y por qué no.
 *
 * Hay DOS interruptores independientes y los dos apagan la escritura: que Notion
 * no esté accesible, y el modo demostración (`?demo=1`), que sustituye los datos
 * por ejemplos. Confundirlos daría un mensaje que no explica nada.
 *
 * Reutiliza la clave `['health']` que ya consulta el Panel, para no duplicar la
 * petición.
 */
export function useEscrituraHabilitada(): EstadoEscritura {
  const queryClient = useQueryClient();
  const salud = useQuery({ queryKey: ['health'], queryFn: getHealth });

  const reintentar = () => void queryClient.invalidateQueries({ queryKey: ['health'] });

  // Mientras se consulta no se acusa a nadie: los botones se deshabilitan, pero
  // sin explicación, porque todavía no se sabe si hay algo que explicar.
  if (salud.isPending) {
    return { habilitada: false, motivo: null, detalle: null, cargando: true, reintentar };
  }

  if (demoModeEnabled()) {
    return {
      habilitada: false,
      motivo:
        'Estás en modo demostración: los datos son de ejemplo y no se guardan en Notion.',
      detalle: null,
      cargando: false,
      reintentar,
    };
  }

  if (salud.isError || !salud.data) {
    return {
      habilitada: false,
      motivo: 'La API no responde, así que ahora mismo no se puede guardar nada.',
      detalle: null,
      cargando: false,
      reintentar,
    };
  }

  if (!salud.data.escrituraHabilitada || salud.data.origenDatos !== 'notion') {
    return {
      habilitada: false,
      motivo:
        'Crear y editar exige escribir en Notion, y ahora mismo se está leyendo del ' +
        'respaldo local. Conecta la integración a la página que contiene las bases.',
      detalle: salud.data.notionError,
      cargando: false,
      reintentar,
    };
  }

  return { habilitada: true, motivo: null, detalle: null, cargando: false, reintentar };
}
