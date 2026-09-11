import { PlusIcon, XIcon } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Props {
  valores: string[];
  onChange: (valores: string[]) => void;
  sugerencias?: string[];
  marcador?: string;
  deshabilitado?: boolean;
}

/**
 * Lista de etiquetas con sugerencias.
 *
 * Las sugerencias no son comodidad: el motor de reglas compara los documentos
 * adjuntos contra los exigidos por el procedimiento, asi que «Estudio de
 * imagenes» tecleado sin tilde cambia el veredicto a DOCUMENTOS_FALTANTES sin
 * ningun error a la vista. Ofrecer la grafia correcta evita el problema antes
 * de que exista.
 */
export function CampoChips({
  valores,
  onChange,
  sugerencias = [],
  marcador = 'Añadir…',
  deshabilitado,
}: Props) {
  const [borrador, setBorrador] = useState('');
  const disponibles = sugerencias.filter((s) => !valores.includes(s));

  const añadir = (valor: string) => {
    const limpio = valor.trim();
    if (limpio && !valores.includes(limpio)) onChange([...valores, limpio]);
    setBorrador('');
  };

  return (
    <div className="space-y-2">
      {valores.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {valores.map((valor) => (
            <Badge key={valor} variant="secondary" className="gap-1">
              {valor}
              <button
                type="button"
                disabled={deshabilitado}
                onClick={() => onChange(valores.filter((v) => v !== valor))}
                aria-label={`Quitar ${valor}`}
                className="opacity-60 hover:opacity-100"
              >
                <XIcon className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Input
          value={borrador}
          disabled={deshabilitado}
          placeholder={marcador}
          onChange={(e) => setBorrador(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              // Sin esto, Enter enviaria el formulario entero.
              e.preventDefault();
              añadir(borrador);
            }
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={deshabilitado || !borrador.trim()}
          onClick={() => añadir(borrador)}
          aria-label="Añadir"
        >
          <PlusIcon />
        </Button>
      </div>

      {disponibles.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {disponibles.slice(0, 8).map((sugerencia) => (
            <button
              key={sugerencia}
              type="button"
              disabled={deshabilitado}
              onClick={() => añadir(sugerencia)}
              className="rounded-full border border-dashed px-2 py-0.5 text-[11px] text-muted-foreground transition-colors hover:border-solid hover:text-foreground disabled:opacity-50"
            >
              + {sugerencia}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
