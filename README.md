# Agente de Pre-Autorización Quirúrgica en Tiempo Real

> Reto 1 del hackIAthon de Viamatica.

Hoy un paciente espera **horas o días** a que su aseguradora autorice una cirugía. Aquí el
informe médico del hospital y la póliza de la aseguradora entran por un agente que resuelve en
**segundos**: dice si el procedimiento está cubierto, si se cumple el periodo de carencia, cuánto
paga cada parte y, si falta algo, exactamente qué falta.

- **Aplicación:** https://preauth.juank.tech
- **API:** https://preauth.juank.tech/api/docs
- **Datos:** cuatro bases de datos de Notion (Pólizas, Informes Médicos, Catálogo de
  Procedimientos y Pre-autorizaciones)

---

## La idea que ordena todo el diseño

Un dictamen de seguros tiene que poder defenderse ante un auditor, y *«lo dijo el modelo»* no es
una defensa. Así que el trabajo está partido en dos, y la frontera es explícita:

**Python decide los números.** La aritmética de la carencia, el deducible, el coaseguro y el tope
anual se calcula en el servidor —en centavos enteros— y se le entrega al modelo **como
herramientas**. El agente orquesta y redacta; no computa.

**El modelo hace lo que un `if` no puede.** Lee prosa clínica escrita por un médico y de ahí
extrae el diagnóstico, su código CIE-10, el procedimiento propuesto y la urgencia. Mapea
«extirpación de la vesícula por vía laparoscópica» al CPT 47562 del catálogo. Juzga si el informe
sustenta clínicamente la cirugía. Detecta en la narrativa una condición previa que no está
declarada en la póliza. Y redacta la resolución para el paciente y la justificación para el
auditor.

Esa frontera se cierra con tres garantías que están **en el código**, no en el prompt:

| Garantía | Cómo se hace cumplir |
| --- | --- |
| El modelo no elige el veredicto | Lo decide la precedencia de las condiciones de la póliza. Si el agente escribe otro, `emitir_dictamen` lo rechaza y le devuelve el correcto. |
| El modelo no inventa cifras | Cada herramienta determinista registra las cantidades que devuelve. Si la carta menciona un monto en balboas que no salió de una herramienta, la emisión se rechaza. |
| El modelo no niega una cirugía | Si duda de la necesidad médica, el caso sube a `REVISION_MEDICA` — nunca baja a `RECHAZADO`. Un agente automático no deniega una operación por su cuenta. |

Y el proceso entero se transmite en vivo: cada herramienta con sus argumentos y su resultado, para
poder rastrear cualquier número del dictamen hasta su origen.

---

## Los cinco veredictos y su precedencia

`APROBADO` · `APROBADO_CON_CONDICIONES` · `DOCUMENTOS_FALTANTES` · `REVISION_MEDICA` · `RECHAZADO`

Cuando fallan varias condiciones a la vez, el motivo que se le cita al asegurado es siempre el
mismo. La primera que aplica gana:

1. Póliza no vigente, en mora o cancelada → **RECHAZADO**
2. Exclusión absoluta del procedimiento → **RECHAZADO**
3. El plan contratado no cubre el procedimiento → **RECHAZADO**
4. Carencia no cumplida y no es urgencia → **RECHAZADO**, indicando desde cuándo sí procede
5. Preexistencia no declarada → **REVISION_MEDICA**
6. Faltan documentos exigidos → **DOCUMENTOS_FALTANTES**, con la lista accionable
7. La suma asegurada no alcanza → **APROBADO_CON_CONDICIONES**
8. Todo conforme → **APROBADO**

Dos decisiones de ese orden que no son obvias:

- **El 5 va antes del 6.** Pedirle papeles a un paciente cuyo caso irá a revisión médica de todos
  modos es mandarlo a una diligencia inútil.
- **Una urgencia exonera la carencia.** Es la excepción estándar en gastos médicos mayores, y sin
  ella el sistema rechazaría una apendicitis aguda — justo el caso en que nadie puede esperar.

La pantalla **Reglas** publica el catálogo completo (carencias por plan, coberturas, exclusiones y
documentos exigidos), para que cualquier dictamen se pueda verificar contra la norma en vez de
tener que creérselo.

---

## Los ocho casos cargados

Cada informe de la demostración recorre un camino de dictamen distinto. Están ahí para poder
demostrar el criterio del agente en vivo sin improvisar datos:

| Informe | Escenario | Veredicto |
| --- | --- | --- |
| `INF-2026-0031` | Colecistitis litiásica, expediente completo | APROBADO |
| `INF-2026-0032` | Meniscectomía con 72 días de afiliación y plan que exige 365 | RECHAZADO (carencia) |
| `INF-2026-0033` | Lipoescultura con fin estético declarado | RECHAZADO (exclusión) |
| `INF-2026-0034` | Discectomía lumbar sin historia clínica ni preanestésica | DOCUMENTOS_FALTANTES |
| `INF-2026-0035` | Hernia inguinal «detectada en 2021», póliza de 2024 sin declararla | REVISION_MEDICA |
| `INF-2026-0036` | Apendicitis aguda: urgencia con carencia incumplida | APROBADO |
| `INF-2026-0037` | Artroplastia de B/. 32.000 con B/. 3.200 de suma disponible | APROBADO_CON_CONDICIONES |
| `INF-2026-0038` | Cataratas con la póliza en mora | RECHAZADO (vigencia) |

`api/tests/test_escenarios.py` afirma estos ocho veredictos contra el motor de reglas, sin modelo:
es la red que impide que un refactor rompa la demostración en silencio.

---

## Cómo trabaja el agente

Bucle agéntico con siete herramientas. Las deterministas están marcadas:

| Herramienta | | Qué hace |
| --- | --- | --- |
| `consultar_poliza` | | Términos de la póliza. Única fuente válida de sus cifras. |
| `consultar_informe` | | El informe del hospital, con el relato clínico completo. |
| `buscar_procedimiento` | **D** | Mapea la prosa del médico a candidatos del catálogo. |
| `registrar_analisis_clinico` | | El modelo entrega aquí su extracción y su juicio clínico. |
| `seleccionar_procedimiento` | **D** | Fija el CPT del caso. Rechaza códigos fuera del catálogo. |
| `evaluar_expediente` | **D** | Vigencia, carencia, cobertura, preexistencias, documentos y desglose. **Determina el veredicto.** |
| `emitir_dictamen` | **D** | Cierra el caso. Valida el veredicto y todas las cifras. |

El expediente (póliza, informe y catálogo) se lee **una vez antes** de arrancar el bucle, así que
las herramientas son funciones puras sobre ese estado: cero red mientras el modelo trabaja. Eso
hace que cada llamada tarde microsegundos, que el resultado sea reproducible y que un límite de
peticiones de Notion no pueda reventar la evaluación a mitad de una demostración.

Modelo: `claude-opus-5` con razonamiento adaptativo resumido y esfuerzo `medium` por defecto — la
aritmética difícil ya la hacen las herramientas, así que el modelo no necesita más.

### Si algo falla

| Fallo | Qué pasa |
| --- | --- |
| No hay `ANTHROPIC_API_KEY` | `POST /api/preautorizaciones/reglas` sigue emitiendo el mismo veredicto con las mismas cifras, solo sin la redacción del modelo. |
| Notion caído o token inválido | Cae a los datos de demostración locales. `GET /api/health` reporta `origen_datos`. |
| El modelo nunca emite el dictamen | Se arma en Python desde las reglas ya calculadas, con plantilla. La demostración nunca termina sin veredicto. |
| El modelo inventa una cifra o cambia el veredicto | La herramienta lo rechaza con el valor correcto y el modelo reintenta. |
| Una herramienta lanza una excepción | Vuelve como `tool_result` con error; el stream continúa. |

---

## Tecnologías

| Capa | Herramientas |
| --- | --- |
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS 4, shadcn/ui, React Router 8, TanStack Query |
| Backend | Python 3.13, FastAPI, SQLModel, Pydantic |
| IA | SDK oficial de Anthropic — bucle agéntico con uso de herramientas, en streaming (SSE) |
| Datos | Notion API (`2025-09-03`) con respaldo local; PostgreSQL para la bitácora |
| Despliegue | Docker, Dokploy, Traefik |

---

## Ponerlo en marcha

### Requisitos

| Herramienta | Versión |
| --- | --- |
| [Docker](https://www.docker.com/products/docker-desktop/) | Compose v2 |
| [Node.js](https://nodejs.org) | 22.22 o superior |
| [pnpm](https://pnpm.io/installation) | 10 o superior |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.9 o superior |

```bash
git clone https://github.com/JuanKsPty/preautorizacion-quirurgica.git
cd preautorizacion-quirurgica
pnpm run setup      # .env, dependencias, contenedores y tablas
```

| Servicio | URL |
| --- | --- |
| Aplicación | http://localhost:5173 |
| API | http://localhost:8000/api/health |
| Documentación de la API | http://localhost:8000/api/docs |

Sin configurar nada más, la aplicación funciona con los datos de demostración y el motor de
reglas. Para que el **agente** razone hace falta una clave de Anthropic en el `.env` de la raíz:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### Conectar tu propio Notion

1. Entra a [notion.so/my-integrations](https://www.notion.so/my-integrations), crea una *New
   integration* y copia el **Internal Integration Secret**.
2. Abre la página padre que contiene las cuatro bases → `···` → **Connections** → agrega esa
   integración. Las bases la heredan.
3. Pon en el `.env` el token y los identificadores de las bases:

```env
NOTION_TOKEN=ntn_...
NOTION_DB_POLIZAS=...
NOTION_DB_INFORMES=...
NOTION_DB_PROCEDIMIENTOS=...
NOTION_DB_PREAUTORIZACIONES=...
```

4. Siembra las bases:

```bash
uv run --directory api python scripts/sembrar_notion.py
```

El script es idempotente y lee de `api/app/repositorios/datos_demo.py`, el mismo módulo que
alimenta el respaldo local — así las dos fuentes no pueden divergir. El propio script documenta
las columnas que cada base necesita.

### Comandos

| Comando | Qué hace |
| --- | --- |
| `pnpm run setup` | Deja todo listo y corriendo desde cero |
| `pnpm dev` | Los contenedores con los logs en vivo |
| `pnpm stop` | Apaga los contenedores |
| `pnpm test` | pytest + Vitest, sin Docker |
| `pnpm lint` | oxlint en el frontend, ruff en la API |
| `pnpm run typecheck` | Comprobación de tipos de TypeScript |
| `pnpm run check:secrets` | Busca credenciales filtradas en el repositorio |
| `pnpm run docker:prod` | La versión compilada servida por nginx (:8080) |

---

## La API

Todo cuelga de `/api` y está documentado en [`/api/docs`](http://localhost:8000/api/docs).

| Método | Ruta | Qué hace |
| --- | --- | --- |
| `GET` | `/api/health` | Estado de la API, de la base, de la IA y origen de los datos |
| `GET` | `/api/polizas` · `/api/polizas/{numero}` | Pólizas |
| `GET` | `/api/informes` · `/api/informes/{codigo}` | Informes médicos con su relato clínico |
| `GET` | `/api/procedimientos` | Catálogo con carencias, coberturas y exclusiones |
| `POST` | `/api/preautorizaciones/evaluar` | **El agente**, en streaming (SSE) |
| `POST` | `/api/preautorizaciones/reglas` | Solo el motor de reglas, sin IA |
| `GET` | `/api/preautorizaciones` | Historial de dictámenes emitidos |
| `GET` | `/api/diagnostico/sse` | Sonda de streaming: cinco eventos, uno por segundo |

### El contrato del stream

```
{"tipo":"inicio","folio":"PA-2026-0031","modelo":"claude-opus-5",…}
{"tipo":"razonamiento","texto":"…"}
{"tipo":"herramienta","fase":"inicio","nombre":"consultar_poliza","argumentos":{}}
{"tipo":"herramienta","fase":"fin","nombre":"consultar_poliza","ok":true,"ms":1,…}
{"tipo":"chequeos","veredicto":"APROBADO","chequeos":[…],"desglose":{…}}
{"tipo":"dictamen","dictamen":{…},"ms_total":8421}
{"tipo":"fin","folio":"PA-2026-0031","veredicto":"APROBADO"}
```

Exactamente un `fin`, siempre. Un latido cada 15 segundos para que ningún proxy corte la conexión
por inactividad.

---

## Estructura

```
.
├── api/                          Backend (FastAPI)
│   ├── app/
│   │   ├── dominio/              ← las reglas. Cero E/S, cero FastAPI.
│   │   │   ├── esquemas.py       Póliza, Procedimiento, Informe, Dictamen
│   │   │   ├── reglas.py         vigencia · carencia · cobertura · documentos
│   │   │   ├── financiero.py     deducible · coaseguro · tope, en centavos
│   │   │   └── veredicto.py      la matriz de precedencia
│   │   ├── agente/
│   │   │   ├── prompt.py         qué le toca al modelo y qué no
│   │   │   ├── herramientas.py   definiciones + despachador + validaciones
│   │   │   └── ejecutor.py       el bucle y los eventos del stream
│   │   ├── repositorios/         Notion · demostración · fábrica
│   │   └── api/routes/           health · catálogo · preautorizaciones
│   ├── scripts/sembrar_notion.py
│   └── tests/                    70 pruebas sobre SQLite en memoria
├── web/                          Frontend (React + Vite)
│   └── src/
│       ├── pages/                Panel · Evaluar · Casos · Reglas
│       ├── components/dictamen/  línea de tiempo, chequeos, desglose
│       ├── hooks/                usePreautorizacion (consume el SSE)
│       └── services/             único sitio que habla con la API
├── Dockerfile.api                contexto de build: la raíz
├── Dockerfile.web                contexto de build: la raíz
└── docker-compose.yml            desarrollo con recarga en caliente
```

Convenciones y decisiones técnicas: [`CLAUDE.md`](CLAUDE.md).

## Licencia

MIT. Ver [LICENSE](LICENSE).
