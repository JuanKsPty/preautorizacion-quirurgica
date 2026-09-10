import { useCallback, useEffect, useRef, useState } from 'react';
import { evaluarConAgente } from '@/services/preautorizacionService';
import type { Chequeo, Desglose, Dictamen, EventoAgente, Veredicto } from '@/types/api';

export type EstadoEvaluacion = 'inactivo' | 'evaluando' | 'listo' | 'error';

/** Una fila de la linea de tiempo que se pinta mientras el agente trabaja. */
export type Paso =
  | { clase: 'razonamiento'; id: string; texto: string }
  | { clase: 'comentario'; id: string; texto: string }
  | {
      clase: 'herramienta';
      id: string;
      nombre: string;
      argumentos: Record<string, unknown>;
      ok?: boolean;
      ms?: number;
      resultado?: Record<string, unknown>;
      error?: string;
    };

export interface Cabecera {
  folio: string;
  modelo: string;
  esfuerzo: string;
  origenDatos: string;
  paciente: string;
  hospital: string;
}

export function usePreautorizacion() {
  const [estado, setEstado] = useState<EstadoEvaluacion>('inactivo');
  const [cabecera, setCabecera] = useState<Cabecera | null>(null);
  const [pasos, setPasos] = useState<Paso[]>([]);
  const [chequeos, setChequeos] = useState<Chequeo[]>([]);
  const [desglose, setDesglose] = useState<Desglose | null>(null);
  const [veredictoPreliminar, setVeredictoPreliminar] = useState<Veredicto | null>(null);
  const [dictamen, setDictamen] = useState<Dictamen | null>(null);
  const [avisos, setAvisos] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msTotal, setMsTotal] = useState<number | null>(null);
  const [msTranscurridos, setMsTranscurridos] = useState(0);

  const abortRef = useRef<AbortController | null>(null);

  // Si el componente se desmonta a mitad del stream, cortamos la peticion.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Cronometro en vivo: el contraste entre estos segundos y las horas o dias
  // que tarda el proceso manual es el argumento del producto, asi que se ve.
  useEffect(() => {
    if (estado !== 'evaluando') return;
    // `evaluar` ya llamo a `reiniciar`, que dejo el cronometro en cero: aqui
    // solo se engancha el reloj.
    const arranque = performance.now();
    const reloj = window.setInterval(
      () => setMsTranscurridos(performance.now() - arranque),
      100
    );
    return () => window.clearInterval(reloj);
  }, [estado]);

  const reiniciar = useCallback(() => {
    abortRef.current?.abort();
    setEstado('inactivo');
    setCabecera(null);
    setPasos([]);
    setChequeos([]);
    setDesglose(null);
    setVeredictoPreliminar(null);
    setDictamen(null);
    setAvisos([]);
    setError(null);
    setMsTotal(null);
    setMsTranscurridos(0);
  }, []);

  const aplicar = useCallback((evento: EventoAgente) => {
    switch (evento.tipo) {
      case 'inicio':
        setCabecera({
          folio: evento.folio,
          modelo: evento.modelo,
          esfuerzo: evento.esfuerzo,
          origenDatos: evento.origen_datos,
          paciente: evento.caso.paciente,
          hospital: evento.caso.hospital,
        });
        break;

      case 'razonamiento':
      case 'comentario': {
        // Los deltas se van pegando al ultimo bloque de su misma clase, para
        // que el razonamiento se lea como un parrafo y no como cien filas.
        const clase = evento.tipo;
        setPasos((previos) => {
          const ultimo = previos.at(-1);
          if (ultimo && ultimo.clase === clase) {
            const copia = [...previos];
            copia[copia.length - 1] = { ...ultimo, texto: ultimo.texto + evento.texto };
            return copia;
          }
          return [...previos, { clase, id: `${clase}-${previos.length}`, texto: evento.texto }];
        });
        break;
      }

      case 'herramienta':
        if (evento.fase === 'inicio') {
          setPasos((previos) => [
            ...previos,
            {
              clase: 'herramienta',
              id: evento.id,
              nombre: evento.nombre,
              argumentos: evento.argumentos,
            },
          ]);
        } else {
          setPasos((previos) =>
            previos.map((paso) =>
              paso.clase === 'herramienta' && paso.id === evento.id
                ? {
                    ...paso,
                    ok: evento.ok,
                    ms: evento.ms,
                    resultado: evento.resultado,
                    error: evento.error,
                  }
                : paso
            )
          );
        }
        break;

      case 'chequeos':
        setChequeos(evento.chequeos);
        setDesglose(evento.desglose);
        setVeredictoPreliminar(evento.veredicto);
        break;

      case 'dictamen':
        setDictamen(evento.dictamen);
        setChequeos(evento.dictamen.chequeos);
        setDesglose(evento.dictamen.desglose);
        setMsTotal(evento.ms_total);
        break;

      case 'aviso':
        setAvisos((previos) => [...previos, evento.mensaje]);
        break;

      case 'error':
        setError(evento.mensaje);
        break;

      case 'fin':
        break;
    }
  }, []);

  const evaluar = useCallback(
    async (codigoInforme: string) => {
      reiniciar();
      setEstado('evaluando');

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await evaluarConAgente(codigoInforme, {
          signal: controller.signal,
          onEvento: aplicar,
        });
        setEstado((actual) => (actual === 'evaluando' ? 'listo' : actual));
      } catch (e) {
        if (controller.signal.aborted) {
          setEstado('inactivo');
          return;
        }
        setError(e instanceof Error ? e.message : 'No se pudo evaluar la solicitud');
        setEstado('error');
      } finally {
        abortRef.current = null;
      }
    },
    [aplicar, reiniciar]
  );

  const cancelar = useCallback(() => abortRef.current?.abort(), []);

  return {
    estado,
    cabecera,
    pasos,
    chequeos,
    desglose,
    veredictoPreliminar,
    dictamen,
    avisos,
    error,
    msTotal,
    msTranscurridos,
    evaluar,
    cancelar,
    reiniciar,
  };
}
