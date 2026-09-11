/**
 * Los ocho informes sembrados sostienen los ocho caminos de dictamen de la
 * demostracion, y estan documentados asi en el README.
 *
 * Editarlos se permite —es una funcion que se pidio— pero la pantalla avisa de
 * cual se esta tocando: quitarle la urgencia a la apendicitis rompe el caso mas
 * ilustrativo sin que nadie se entere hasta que toca enseñarlo.
 */
export const ESCENARIOS_DEMO: Record<string, string> = {
  'INF-2026-0031': 'aprobación limpia',
  'INF-2026-0032': 'carencia incumplida',
  'INF-2026-0033': 'exclusión estética',
  'INF-2026-0034': 'expediente documental incompleto',
  'INF-2026-0035': 'preexistencia sin declarar',
  'INF-2026-0036': 'urgencia que exonera la carencia',
  'INF-2026-0037': 'suma asegurada insuficiente',
  'INF-2026-0038': 'póliza en mora',
};
