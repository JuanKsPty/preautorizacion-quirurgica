import { jsPDF } from 'jspdf';
import { dinero, fechaHora, VEREDICTO } from '@/lib/formato';
import type { DictamenRegistrado } from '@/types/api';

const MARGEN = 16;
const ANCHO = 178;
const ALTO_PAGINA = 280;

/** Genera un resumen documental descargable sin enviar datos a un servicio externo. */
export function exportarDictamenPdf(registro: DictamenRegistrado): void {
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
  let y = 18;

  const saltoPagina = (alto: number) => {
    if (y + alto <= ALTO_PAGINA) return;
    pdf.addPage();
    y = 18;
  };

  const parrafo = (texto: string, tamano = 10, negrita = false) => {
    pdf.setFont('helvetica', negrita ? 'bold' : 'normal');
    pdf.setFontSize(tamano);
    const lineas = pdf.splitTextToSize(texto, ANCHO) as string[];
    const alto = Math.max(5, lineas.length * 4.8);
    saltoPagina(alto);
    pdf.text(lineas, MARGEN, y);
    y += alto;
  };

  const separador = () => {
    saltoPagina(6);
    pdf.setDrawColor(220, 225, 226);
    pdf.line(MARGEN, y, MARGEN + ANCHO, y);
    y += 7;
  };

  pdf.setTextColor(20, 35, 36);
  parrafo('PRE-AUTORIZACIÓN QUIRÚRGICA', 18, true);
  parrafo('Dictamen de autorización', 11);
  y += 2;
  separador();

  parrafo(`Folio: ${registro.folio}`, 11, true);
  parrafo(`Fecha: ${fechaHora(registro.createdAt)}`);
  parrafo(`Paciente: ${registro.paciente}`);
  parrafo(`Póliza: ${registro.numeroPoliza}`);
  parrafo(`Procedimiento: ${registro.procedimiento ?? 'No identificado'}`);
  y += 2;

  const estilo = VEREDICTO[registro.veredicto];
  pdf.setTextColor(18, 120, 120);
  parrafo(`VEREDICTO: ${estilo.etiqueta.toUpperCase()}`, 12, true);
  pdf.setTextColor(20, 35, 36);
  parrafo(registro.dictamen?.resumen ?? 'Dictamen emitido por el sistema.');
  y += 2;

  if (registro.dictamen?.desglose) {
    separador();
    parrafo('Resumen económico', 11, true);
    parrafo(`Monto cotizado: ${dinero(registro.dictamen.desglose.monto_cotizado)}`);
    parrafo(`Cobertura: ${registro.dictamen.desglose.cobertura_porcentaje.toFixed(0)}%`);
    parrafo(`Cubre la aseguradora: ${dinero(registro.dictamen.desglose.cubierto_aseguradora)}`);
    parrafo(`A cargo del paciente: ${dinero(registro.dictamen.desglose.a_cargo_paciente)}`);
  }

  if (registro.dictamen?.documentos_faltantes.length) {
    separador();
    parrafo('Documentos pendientes', 11, true);
    for (const documento of registro.dictamen.documentos_faltantes) parrafo(`- ${documento}`);
  }

  if (registro.dictamen?.chequeos.length) {
    separador();
    parrafo('Verificaciones', 11, true);
    for (const item of registro.dictamen.chequeos) {
      parrafo(`${item.nombre}: ${item.estado.replaceAll('_', ' ')}. ${item.detalle}`);
    }
  }

  if (registro.dictamen?.carta_paciente) {
    separador();
    parrafo('Resolución para el paciente', 11, true);
    parrafo(registro.dictamen.carta_paciente);
  }

  pdf.setFontSize(8);
  pdf.setTextColor(115, 125, 126);
  pdf.text('Documento generado por Pre-Autorización Quirúrgica.', MARGEN, 290);
  pdf.save(`dictamen-${registro.folio.toLowerCase()}.pdf`);
}
