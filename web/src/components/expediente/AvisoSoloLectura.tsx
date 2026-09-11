import { DatabaseIcon, RotateCcwIcon } from 'lucide-react';
import { Link } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import type { EstadoEscritura } from '@/hooks/useEscrituraHabilitada';

/**
 * Explica por que no se puede guardar, sin bloquear el formulario.
 *
 * Los campos siguen habilitados a proposito: deshabilitar quince entradas
 * parece un fallo, y ademas la extraccion con IA NO necesita Notion, asi que la
 * parte que mejor demuestra el producto se puede seguir enseñando. Lo unico que
 * se apaga son los botones de guardar.
 */
export function AvisoSoloLectura({ estado }: { estado: EstadoEscritura }) {
  if (estado.habilitada || estado.cargando) return null;

  return (
    <Alert>
      <DatabaseIcon />
      <AlertTitle>No se puede guardar: Notion no está disponible</AlertTitle>
      <AlertDescription className="space-y-2">
        <p>{estado.motivo}</p>
        {estado.detalle && (
          <p className="rounded-lg bg-muted px-2.5 py-1.5 font-mono text-xs break-words">
            {estado.detalle}
          </p>
        )}
        <p>
          Puedes escribir y extraer datos, pero no guardarlos. Revisa el{' '}
          <Link to="/" className="underline underline-offset-4">
            estado del sistema
          </Link>
          .
        </p>
        <Button variant="outline" size="sm" onClick={estado.reintentar}>
          <RotateCcwIcon /> Reintentar
        </Button>
      </AlertDescription>
    </Alert>
  );
}
