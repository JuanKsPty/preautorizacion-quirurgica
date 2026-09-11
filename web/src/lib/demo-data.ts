import type { Desglose, Dictamen, DictamenRegistrado, EstadoChequeo, Veredicto } from '@/types/api';

const chequeo = (nombre: string, estado: EstadoChequeo, detalle: string) => ({
  nombre,
  estado,
  detalle,
});

const desglose = (
  montoCotizado: number,
  coberturaPorcentaje: number,
  cubiertoAseguradora: number,
  aCargoPaciente: number
): Desglose => ({
  monto_cotizado: montoCotizado,
  cobertura_porcentaje: coberturaPorcentaje,
  deducible_aplicado: 0,
  coaseguro_asegurado: aCargoPaciente,
  no_reconocido_por_plan: 0,
  exceso_sobre_tope: 0,
  cubierto_aseguradora: cubiertoAseguradora,
  a_cargo_paciente: aCargoPaciente,
  tope_disponible_antes: 15000,
  tope_disponible_despues: Math.max(0, 15000 - cubiertoAseguradora),
  excede_tope: false,
});

function crearRegistro({
  id,
  folio,
  veredicto,
  paciente,
  procedimiento,
  cpt,
  cie10,
  resumen,
  documentosFaltantes = [],
  montoCotizado,
  cubiertoAseguradora,
  aCargoPaciente,
  createdAt,
  desgloseActivo = true,
}: {
  id: number;
  folio: string;
  veredicto: Veredicto;
  paciente: string;
  procedimiento: string | null;
  cpt: string | null;
  cie10: string | null;
  resumen: string;
  documentosFaltantes?: string[];
  montoCotizado: number;
  cubiertoAseguradora: number;
  aCargoPaciente: number;
  createdAt: string;
  desgloseActivo?: boolean;
}): DictamenRegistrado {
  const dictamen: Dictamen = {
    folio,
    veredicto,
    resumen,
    numero_poliza: `POL-DEMO-${String(id).padStart(3, '0')}`,
    codigo_informe: `INF-DEMO-${String(id).padStart(3, '0')}`,
    paciente,
    cpt_identificado: cpt,
    procedimiento_identificado: procedimiento,
    cie10_identificado: cie10,
    motivos: [resumen],
    documentos_faltantes: documentosFaltantes,
    chequeos: [
      chequeo('Vigencia de la póliza', 'conforme', 'La póliza se encuentra vigente.'),
      chequeo(
        'Cobertura del procedimiento',
        veredicto === 'RECHAZADO' ? 'no_conforme' : 'conforme',
        veredicto === 'RECHAZADO'
          ? 'El procedimiento está excluido del plan contratado.'
          : 'El procedimiento está contemplado por el plan contratado.'
      ),
      chequeo(
        'Documentación clínica',
        documentosFaltantes.length > 0 ? 'no_conforme' : 'conforme',
        documentosFaltantes.length > 0
          ? 'Faltan documentos para cerrar la evaluación.'
          : 'Los documentos adjuntos cumplen los requisitos.'
      ),
    ],
    desglose: desgloseActivo
      ? desglose(
          montoCotizado,
          montoCotizado ? (cubiertoAseguradora / montoCotizado) * 100 : 0,
          cubiertoAseguradora,
          aCargoPaciente
        )
      : null,
    carta_paciente: `${resumen} Paciente: ${paciente}.`,
    justificacion_tecnica:
      'Este registro pertenece al conjunto de datos de prueba del branch y sirve para validar la lectura del historial y la exportación documental.',
  };

  return {
    id,
    folio,
    veredicto,
    numeroPoliza: dictamen.numero_poliza,
    codigoInforme: dictamen.codigo_informe,
    paciente,
    cpt,
    procedimiento,
    montoCotizado,
    cubiertoAseguradora,
    aCargoPaciente,
    msTotal: (id - 9000) * 730,
    origenDatos: 'demo',
    notionUrl: null,
    dictamen,
    createdAt: new Date(createdAt),
  };
}

/** Datos locales activables solo con ?demo=1 para probar el historial. */
export const DEMO_DICTAMENES: DictamenRegistrado[] = [
  crearRegistro({
    id: 9001,
    folio: 'PA-DEMO-001',
    veredicto: 'APROBADO',
    paciente: 'María Elena Ríos',
    procedimiento: 'Colecistectomía laparoscópica',
    cpt: '47562',
    cie10: 'K80.1',
    resumen: 'La cirugía queda pre-autorizada y cumple las condiciones de la póliza.',
    montoCotizado: 5200,
    cubiertoAseguradora: 4680,
    aCargoPaciente: 520,
    createdAt: '2026-09-10T16:25:00Z',
  }),
  crearRegistro({
    id: 9002,
    folio: 'PA-DEMO-002',
    veredicto: 'APROBADO_CON_CONDICIONES',
    paciente: 'Carlos Andrés Méndez',
    procedimiento: 'Reparación de hernia inguinal',
    cpt: '49505',
    cie10: 'K40.9',
    resumen: 'Procede con una participación del paciente por encima del deducible disponible.',
    montoCotizado: 4100,
    cubiertoAseguradora: 3075,
    aCargoPaciente: 1025,
    createdAt: '2026-09-10T15:40:00Z',
  }),
  crearRegistro({
    id: 9003,
    folio: 'PA-DEMO-003',
    veredicto: 'DOCUMENTOS_FALTANTES',
    paciente: 'Lucía Fernanda Ortega',
    procedimiento: 'Artroscopia de rodilla',
    cpt: '29881',
    cie10: 'M23.2',
    resumen: 'No se puede resolver todavía: falta documentación del expediente.',
    documentosFaltantes: ['Resonancia magnética', 'Orden médica firmada'],
    montoCotizado: 3600,
    cubiertoAseguradora: 0,
    aCargoPaciente: 0,
    desgloseActivo: false,
    createdAt: '2026-09-10T14:15:00Z',
  }),
  crearRegistro({
    id: 9004,
    folio: 'PA-DEMO-004',
    veredicto: 'REVISION_MEDICA',
    paciente: 'José Miguel Batista',
    procedimiento: 'Artroplastia total de cadera',
    cpt: '27130',
    cie10: 'M16.1',
    resumen: 'El caso pasa a revisión médica por una condición clínica previa.',
    montoCotizado: 12500,
    cubiertoAseguradora: 0,
    aCargoPaciente: 0,
    desgloseActivo: false,
    createdAt: '2026-09-10T12:50:00Z',
  }),
  crearRegistro({
    id: 9005,
    folio: 'PA-DEMO-005',
    veredicto: 'RECHAZADO',
    paciente: 'Ana Sofía Herrera',
    procedimiento: 'Cirugía bariátrica',
    cpt: '43644',
    cie10: 'E66.9',
    resumen: 'No procede según las condiciones de la póliza: el procedimiento está excluido.',
    montoCotizado: 9800,
    cubiertoAseguradora: 0,
    aCargoPaciente: 9800,
    desgloseActivo: false,
    createdAt: '2026-09-10T11:20:00Z',
  }),
];

const DEMO_MODE_KEY = 'preauth-demo-mode';

export function demoModeEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  const queryEnabled = new URLSearchParams(window.location.search).get('demo') === '1';
  if (queryEnabled) window.sessionStorage.setItem(DEMO_MODE_KEY, '1');
  return queryEnabled || window.sessionStorage.getItem(DEMO_MODE_KEY) === '1';
}
