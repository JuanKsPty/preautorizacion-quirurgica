import { apiFetch } from './http';
import type {
  Informe,
  InformeDto,
  InformeEntradaDto,
  NivelPlan,
  Poliza,
  PolizaDto,
  PolizaEntradaDto,
  Procedimiento,
  ProcedimientoDto,
  RespuestaEscritura,
  RespuestaInformeDto,
  RespuestaPolizaDto,
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

// ---------------------------------------------------------------- escritura
//
// Los DTO de entrada son los que ya habla la API, asi que no hay un modelo de
// dominio propio para escribir: el formulario produce directamente esa forma.
// Traducirla a camelCase para volver a traducirla al enviar solo añadiria dos
// sitios mas donde equivocarse.

export async function obtenerPoliza(numero: string): Promise<Poliza> {
  return aPoliza(await apiFetch<PolizaDto>(`/polizas/${encodeURIComponent(numero)}`));
}

export async function obtenerInforme(codigo: string): Promise<Informe> {
  return aInforme(await apiFetch<InformeDto>(`/informes/${encodeURIComponent(codigo)}`));
}

function aRespuestaPoliza(dto: RespuestaPolizaDto): RespuestaEscritura<Poliza> {
  return { registro: aPoliza(dto.poliza), notionUrl: dto.notion_url, avisos: dto.avisos };
}

function aRespuestaInforme(dto: RespuestaInformeDto): RespuestaEscritura<Informe> {
  return { registro: aInforme(dto.informe), notionUrl: dto.notion_url, avisos: dto.avisos };
}

export async function crearPoliza(
  entrada: PolizaEntradaDto & { numero?: string }
): Promise<RespuestaEscritura<Poliza>> {
  return aRespuestaPoliza(
    await apiFetch<RespuestaPolizaDto>('/polizas', { method: 'POST', body: entrada })
  );
}

export async function actualizarPoliza(
  numero: string,
  entrada: PolizaEntradaDto
): Promise<RespuestaEscritura<Poliza>> {
  return aRespuestaPoliza(
    await apiFetch<RespuestaPolizaDto>(`/polizas/${encodeURIComponent(numero)}`, {
      method: 'PUT',
      body: entrada,
    })
  );
}

export async function crearInforme(
  entrada: InformeEntradaDto & { codigo?: string }
): Promise<RespuestaEscritura<Informe>> {
  return aRespuestaInforme(
    await apiFetch<RespuestaInformeDto>('/informes', { method: 'POST', body: entrada })
  );
}

export async function actualizarInforme(
  codigo: string,
  entrada: InformeEntradaDto
): Promise<RespuestaEscritura<Informe>> {
  return aRespuestaInforme(
    await apiFetch<RespuestaInformeDto>(`/informes/${encodeURIComponent(codigo)}`, {
      method: 'PUT',
      body: entrada,
    })
  );
}
