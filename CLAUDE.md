# Guia del proyecto para Claude Code

Agente de pre-autorizacion quirurgica: **React + Vite (TypeScript)** en `web/` y **FastAPI
(Python 3.13)** en `api/`. Un solo `.env` en la raiz.

**La aplicacion corre en contenedores** (`docker compose`: `web`, `api`, `db`) con el codigo
montado como volumen, asi que al guardar un archivo se recarga solo. **Las herramientas corren en
la maquina** (tests, linter, tipos) y no necesitan Docker.

## Comandos

```bash
pnpm run setup           # .env + dependencias + contenedores
pnpm dev                 # docker compose up: web :5173, api :8000 (docs /api/docs)
pnpm run dev:build       # reconstruye las imagenes (tras cambiar dependencias)
pnpm stop                # apaga los contenedores
pnpm run logs            # logs en vivo (logs:api, logs:web)

pnpm test                # pytest + vitest, en la maquina
pnpm lint                # oxlint (web) + ruff (api)
pnpm run typecheck       # tsc -b
pnpm run check:secrets   # busca credenciales filtradas

uv run --directory api python scripts/sembrar_notion.py    # siembra Notion
```

- Comandos de la aplicacion -> dentro del contenedor: `docker compose exec api <comando>`.
- Comandos de calidad -> en la maquina: `uv run --directory api ...` y `pnpm --filter web ...`.
  El `--directory` importa: sin el, `app.main` no se resuelve.

## La frontera que ordena el diseno

**`api/app/dominio/` decide los numeros.** Carencia, deducible, coaseguro y tope se calculan ahi,
sin E/S y sin FastAPI, y se le exponen al modelo como herramientas. **El modelo lee prosa clinica,
mapea al catalogo, aporta juicio medico y redacta.** No calcula y no elige el veredicto.

Tres cosas que se hacen cumplir en codigo, no en el prompt, y que **no se relajan**:

1. `emitir_dictamen` rechaza un veredicto distinto al que calculo `evaluar_expediente`.
2. `emitir_dictamen` rechaza cualquier cifra en balboas que no haya devuelto una herramienta
   (`EstadoEjecucion.cifras_permitidas`).
3. El juicio clinico del modelo solo puede BAJAR en la escala: `informe_sustenta_procedimiento:
   false` produce `REVISION_MEDICA`, jamas `RECHAZADO`. Un agente automatico no niega una cirugia.

## Donde va cada cosa

| Necesitas... | Archivo |
| --- | --- |
| Una regla de negocio nueva | `api/app/dominio/reglas.py` (+ prueba en `api/tests/test_reglas.py`) |
| Cambiar la precedencia del veredicto | `api/app/dominio/veredicto.py` (+ `test_veredicto.py`) |
| Una herramienta nueva del agente | `api/app/agente/herramientas.py`: definicion en `HERRAMIENTAS` y rama en `ejecutar_herramienta` |
| Un endpoint nuevo | `api/app/api/routes/<tema>.py` + registrarlo en `api/app/api/router.py` |
| Una tabla nueva | `api/app/models/<entidad>.py` (tabla + `*Public` juntos) + exportarla en `api/app/models/__init__.py` |
| Una columna nueva de Notion | `api/app/repositorios/propiedades.py` o `notion.py` (leer) **y** `api/app/repositorios/escritura.py` (escribir). El seeder importa de ahi, asi que no hay que tocarlo |
| Una pantalla nueva | `web/src/pages/<Nombre>Page.tsx` + ruta en `web/src/App.tsx` + enlace en `Navbar.tsx` |
| Llamar a la API | Un modulo en `web/src/services/`, nunca `fetch` dentro de un componente |
| Un tipo de la API | `web/src/types/api.ts` (DTO en snake_case + modelo de dominio en camelCase) |
| Una variable de entorno | `.env.example` **y** `api/app/core/config.py` (o `web/src/lib/env.ts` si es `VITE_*`) **y** ambos compose |
| Un componente de UI | `pnpm dlx shadcn@latest add <componente>` (no escribirlo a mano) |

## Convenciones

- **La capa `services/` es la unica que habla con la API.** Usa `apiFetch` de
  `web/src/services/http.ts`: ya pone la base URL y normaliza los errores a `ApiError`.
- **DTO -> dominio en el service.** La API devuelve snake_case y fechas como string; la UI consume
  camelCase y `Date`. La conversion vive en el service (`catalogoService.ts` como plantilla). El
  `Dictamen` es la excepcion: viaja en snake_case y se consume tal cual, porque es un documento.
- **Datos del servidor** con TanStack Query; estado local con `useState`.
- **Textos de cara al usuario en espanol**, incluidos los mensajes de error de la API.
- **Python**: nombres de dominio en espanol, en ingles cuando son de FastAPI/SQLModel. `ruff`
  manda (linea de 100).
- **TypeScript estricto**: `verbatimModuleSyntax` obliga a `import type`, y `erasableSyntaxOnly`
  prohibe `enum` y propiedades en el constructor.
- El alias `@/` apunta a `web/src`. `web/src/components/ui/` es codigo de shadcn: no se edita ni se
  lintea.
- **El color nunca es el unico canal.** Cada veredicto lleva icono y etiqueta de texto ademas de
  color. Los tokens estan en `web/src/index.css` y se consumen como `bg-exito-fondo text-exito`.

## Decisiones ya tomadas (no re-discutir)

- **Escribir NO tiene respaldo.** La lectura degrada a los datos locales cuando
  Notion falla; la escritura no, y `RepositorioDemo` no recibe metodos de
  escritura ni siquiera como stubs que lancen: `runtime_checkable` solo
  comprueba que el atributo exista, asi que un stub haria que
  `isinstance(demo, RepositorioEscritura)` diera True. Guardar en un sitio que
  se pierde al reiniciar es peor que no guardar.
- **Los nombres de columna de Notion viven en UN sitio**: `escritura.py` para
  escribir, `propiedades.py`/`notion.py` para leer. Los helpers de escritura
  llevan prefijo `a_` porque hay funciones homonimas que leen.
- **La API de Notion es asimetrica**: al escribir un title/rich_text se manda
  `{"text": {"content"}}`, pero al leerlo devuelve ADEMAS `plain_text`, que es
  el campo que usan los extractores. `tests/test_escritura.py` lo modela.
- **`update_markdown` no se usa** para reescribir el relato: da la vuelta por
  Markdown y un texto con guiones o numeracion vuelve como `bulleted_list_item`,
  que `_cuerpo()` no lee. Se usa `erase_content` + `append`, con respaldo.
- **Una escritura correcta reabre la lectura** (`notificar_escritura_exitosa`):
  si no, un registro recien creado no aparece durante los 60 s de degradacion.
- **El dinero en el frontend nunca es `type="number"`** y `fechaInput` nunca usa
  `toISOString()` (convierte a UTC y en Panama devuelve el dia anterior).
- **Los formularios producen el DTO directamente**, en snake_case: traducir a
  camelCase para volver a traducir al enviar solo añade sitios donde
  equivocarse. Misma decision que con `Dictamen`.

- **El dinero se calcula en centavos enteros** (`dominio/financiero.py`). Con `float` el resultado
  sale bien al centavo pero el invariante `paciente + aseguradora == cotizado` deja de
  comprobarse: 8960.21 + 5540.12 da 14500.329999999998.
- **El expediente se lee UNA VEZ antes del bucle** del agente. Las herramientas son funciones
  puras sobre ese snapshot: cero red mientras el modelo trabaja. Asi un limite de peticiones de
  Notion no puede reventar una evaluacion a mitad de una demostracion.
- **Bucle manual, no `tool_runner`**: hace falta un evento SSE por cada delta de razonamiento y por
  cada herramienta, y poder cambiar `tool_choice` a mitad de la ejecucion para escalar. Ademas el
  runner es beta.
- **`AsyncClient` de Notion, no `Client`.** El cliente sincrono es httpx bloqueante y llamarlo
  dentro del generador que transmite el SSE congelaria el event loop.
- **Desde la version 2025-09-03 de la API de Notion, `databases.query` NO EXISTE.** Las consultas
  van a `data_sources.query`; el `data_source_id` sale de `databases.retrieve(...)` y se cachea.
- **El relato clinico va en el CUERPO de la pagina de Notion**, no en una columna: `rich_text`
  tope a 2000 caracteres y un informe se acerca demasiado.
- **`web/nginx.conf` pone el upstream de `/api` en una VARIABLE.** Con un nombre literal, nginx lo
  resuelve al arrancar y sale con "host not found in upstream" si el servicio no existe — el
  contenedor entraria en bucle de reinicio. En Dokploy ese bloque no se usa: son dos aplicaciones
  separadas y Traefik enruta `/api` directo a la API.
- **Los dos Dockerfiles viven en la raiz** (`Dockerfile.api`, `Dockerfile.web`) y los dos usan la
  raiz como contexto de build. Un solo contexto, sin asimetrias.
- **`X-Accel-Buffering: no` y `proxy_buffering off` no se quitan**, y no se anade `GZipMiddleware`
  ni un middleware `compress` en Traefik: cualquiera de los tres congela el SSE.
- **`--forwarded-allow-ips '*'`** en el `CMD` de produccion: sin el, uvicorn descarta las cabeceras
  `X-Forwarded-*` de Traefik y las redirecciones salen como `http://`.
- **`AUTO_CREATE_TABLES=true`**, sin Alembic. La bitacora es append-only y no hay nada que migrar;
  `alembic/versions/` esta vacio, asi que `upgrade head` no crearia ninguna tabla.
- **Las pruebas corren sobre SQLite en memoria** (`tests/conftest.py`), sin Docker. El agente se
  prueba con un cliente de Anthropic falso (`tests/test_agente.py`).
- **No hay autenticacion.** Un muro de login solo estorbaria a quien abre el enlace publico a
  evaluar la demostracion.

## Al terminar una tarea

1. `pnpm test`, `pnpm lint` y `pnpm run typecheck` en verde.
2. Si tocaste las reglas, `api/tests/test_escenarios.py` sigue dando los ocho veredictos.
3. Si tocaste la API, comprueba el endpoint en `/api/docs` o con `curl`.
4. Si tocaste dependencias, **commitea los lockfiles**: `uv.lock` y `pnpm-lock.yaml`. Sin eso el
   build de Docker falla con `--frozen-lockfile` / `uv sync --locked`.
