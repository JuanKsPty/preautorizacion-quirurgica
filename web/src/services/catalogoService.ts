import { apiFetch } from './http';
import type {
  Informe,
  InformeDto,
  NivelPlan,
  Poliza,
  PolizaDto,
  Procedimiento,
  ProcedimientoDto,
} from '@/types/api';

const aPoliza = (dto: PolizaDto): Poliza => ({
  numero: dto.numero,
  titular: dto.titular,
  cedula: dto.cedula,
  plan: dto.plan,
  estado: dto.estado,
  inicioVigencia: new Date(`${dto.inicio_vigencia}T00:00:00`),
  finVigencia: new Date(`${dto.fin_vigencia}T00:00:00`),
  deducibleAnual: dto.deducible_anual,
  deducibleConsumido: dto.deducible_consumido,
  coaseguroPorcentaje: dto.coaseguro_porcentaje,
  topeAnual: dto.tope_anual,
  topeConsumido: dto.tope_consumido,
  redPreferente: dto.red_preferente,
  preexistenciasDeclaradas: dto.preexistencias_declaradas,
  dependientes: dto.dependientes,
});

const aInforme = (dto: InformeDto): Informe => ({
  codigo: dto.codigo,
  paciente: dto.paciente,
  cedula: dto.cedula,
  numeroPoliza: dto.numero_poliza,
  hospital: dto.hospital,
  medicoTratante: dto.medico_tratante,
  especialidad: dto.especialidad,
  fechaInforme: new Date(`${dto.fecha_informe}T00:00:00`),
  fechaCirugiaPropuesta: new Date(`${dto.fecha_cirugia_propuesta}T00:00:00`),
  esEmergencia: dto.es_emergencia,
  montoCotizado: dto.monto_cotizado,
  documentosAdjuntos: dto.documentos_adjuntos,
  texto: dto.texto,
});

const aProcedimiento = (dto: ProcedimientoDto): Procedimiento => ({
  cpt: dto.cpt,
  nombre: dto.nombre,
  sinonimos: dto.sinonimos,
  categoria: dto.categoria,
  carenciaDias: dto.carencia_dias as Record<NivelPlan, number>,
  coberturaPorcentaje: dto.cobertura_porcentaje as Record<NivelPlan, number>,
  documentosRequeridos: dto.documentos_requeridos,
  exclusion: dto.exclusion,
});

export async function listarPolizas(): Promise<Poliza[]> {
  return (await apiFetch<PolizaDto[]>('/polizas')).map(aPoliza);
}

export async function listarInformes(): Promise<Informe[]> {
  return (await apiFetch<InformeDto[]>('/informes')).map(aInforme);
}

export async function listarProcedimientos(): Promise<Procedimiento[]> {
  return (await apiFetch<ProcedimientoDto[]>('/procedimientos')).map(aProcedimiento);
}
