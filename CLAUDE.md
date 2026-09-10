# Guia del proyecto para Claude Code

Plantilla de hackathon: **React + Vite (TypeScript)** en `web/` y **FastAPI
(Python 3.13)** en `api/`. Un solo `.env` en la raiz.

**La aplicacion corre en contenedores** (`docker compose`: `web`, `api`, `db`) con
el codigo montado como volumen, asi que al guardar un archivo se recarga solo.
**Las herramientas corren en la maquina** (tests, linter, tipos) y no necesitan
Docker.

## Comandos

```bash
pnpm run setup           # .env + dependencias + contenedores + datos demo
pnpm dev                 # docker compose up: web :5173, api :8000 (docs /api/docs)
pnpm run dev:build       # reconstruye las imagenes (tras cambiar dependencias)
pnpm stop                # apaga los contenedores
pnpm run logs            # logs en vivo (logs:api, logs:web)
pnpm run seed            # datos de demostracion (idempotente)

pnpm test                # pytest + vitest, en la maquina
pnpm lint                # oxlint (web) + ruff (api)
pnpm run typecheck       # tsc -b
pnpm run check:secrets   # busca credenciales filtradas
```

**Donde se ejecuta cada cosa**

- Comandos de la aplicacion -> dentro del contenedor:
  `docker compose exec api <comando>` (hay atajos: `seed`, `db:revision`,
  `db:migrate`, `shell:api`).
- Comandos de calidad -> en la maquina: `uv run --directory api ...` y
  `pnpm --filter web ...`. El `--directory` importa: sin el, `app.main` no se
  resuelve.
- Sin Docker: `pnpm run dev:host` (procesos locales) y `pnpm run seed:host`,
  con `DATABASE_URL=sqlite:///./app.db` en el `.env`.

## Donde va cada cosa

| Necesitas... | Archivo |
| --- | --- |
| Un endpoint nuevo | `api/app/api/routes/<tema>.py` + registrarlo en `api/app/api/router.py` |
| Una tabla nueva | `api/app/models/<entidad>.py` (tabla + `*Create` + `*Update` + `*Public` juntos) + exportarla en `api/app/models/__init__.py` |
| Una pantalla nueva | `web/src/pages/<Nombre>Page.tsx` + ruta en `web/src/App.tsx` |
| Llamar a la API | Un modulo en `web/src/services/`, nunca `fetch` dentro de un componente |
| Un tipo de la API | `web/src/types/api.ts` (DTO en snake_case + modelo de dominio en camelCase) |
| Una variable de entorno | `.env.example` **y** `api/app/core/config.py` (o `web/src/lib/env.ts` si es `VITE_*`) |
| Un componente de UI | `pnpm dlx shadcn@latest add <componente>` (no escribirlo a mano) |

## Convenciones

- **La capa `services/` es la unica que habla con la API.** Usa `apiFetch` de
  `web/src/services/http.ts`: ya pone la base URL, el token y normaliza los
  errores a `ApiError` (`status` + `message`).
- **DTO -> dominio en el service.** La API devuelve snake_case y fechas como
  string; la UI consume camelCase y `Date`. La conversion vive en el service
  (mira `itemsService.ts` como plantilla).
- **Formularios** con `react-hook-form` + `zod` (`zodResolver`). Zod v4: usa
  `z.email('mensaje')`, no `z.string().email()`.
- **Datos del servidor** con TanStack Query; estado local con `useState`. No
  metas datos de la API en un store global.
- **Textos de cara al usuario en espanol**, incluidos los mensajes de error de la
  API: son parte de la interfaz, no un detalle tecnico.
- **Python**: nombres de funciones y variables en espanol cuando son del dominio,
  en ingles cuando son de FastAPI/SQLModel. `ruff` manda (linea de 100).
- **TypeScript estricto**: `verbatimModuleSyntax` obliga a `import type` para los
  tipos, y `erasableSyntaxOnly` prohibe `enum` y propiedades en el constructor.
- El alias `@/` apunta a `web/src`. Si algun dia el CLI de shadcn crea una carpeta
  literal `@/`, es porque falta `paths` en `web/tsconfig.json`.
- `web/src/components/ui/` es codigo generado por shadcn: no se edita ni se lintea.

## Decisiones ya tomadas (no re-discutir)

- **React Router 8**, no TanStack Router. Se evaluo: TanStack gana en tipado y
  search params, pero mete un plugin de Vite y un `routeTree.gen.ts` generado en
  el camino del build, sin ganar nada que este proyecto necesite. En v8 **no existe
  `react-router-dom`**: se importa todo de `react-router`.
- **JWT en `localStorage`**, no cookie httpOnly. Mas rapido de montar; el tradeoff
  (XSS) esta documentado en `http.ts` y en el README.
- **Argon2** (`pwdlib`) para las contrasenas, no bcrypt.
- **CORS como string** en `Settings`, no `list[str]`: pydantic-settings intenta
  parsear las listas como JSON y `"a,b"` haria fallar el arranque.
- **El arranque es `docker compose up`**, no procesos locales: un solo comando
  levanta frontend, API y base, y nadie tiene que instalar PostgreSQL. El compose
  de desarrollo monta el codigo y recarga en caliente; `docker-compose.prod.yml`
  es la version compilada tras nginx.
- **El entorno de Python del contenedor vive en `/opt/venv`**, fuera de `/app`:
  si estuviera en `/app/.venv`, el volumen del codigo lo taparia con el `.venv`
  del host, que esta compilado para macOS.
- **`postgres:18+` monta el volumen en `/var/lib/postgresql`**, no en
  `.../postgresql/data` como las versiones anteriores; con el path viejo el
  contenedor se niega a arrancar.
- **El `DATABASE_URL` del `.env` es el del host** (`127.0.0.1:5432`, para Alembic
  y los comandos locales); dentro de compose la variable se sobreescribe con
  `db:5432`, que es como se llama la base en la red de contenedores.
- **`AUTO_CREATE_TABLES=true`** crea las tablas al arrancar. Cuando el esquema
  tenga que cambiar sin perder datos: pon el flag en `false` y usa
  `pnpm run db:revision "..."` + `pnpm run db:migrate`. No uses las dos cosas a la vez.
- **Las pruebas de la API corren sobre SQLite en memoria** (`tests/conftest.py`),
  para que la suite no dependa de Docker.
- El proxy de Vite apunta a `127.0.0.1:8000`, no a `localhost`: con `localhost`
  Node puede resolver `::1` y uvicorn escucha en IPv4.
- Los headers `X-Accel-Buffering: no` y `proxy_buffering off` del chat no se
  quitan: sin ellos nginx bufferea el SSE y el streaming se ve congelado.

## Al terminar una tarea

1. `pnpm test` y `pnpm lint` en verde.
2. Si tocaste la API, comprueba el endpoint en `/api/docs` o con `curl`.
3. Si tocaste el modelo de datos, `pnpm run seed` sigue funcionando.
   Si tocaste dependencias, `pnpm run dev:build` reconstruye las imagenes.
4. Los commits generados con asistencia de IA llevan el trailer
   `Co-Authored-By: ...` para que el historial lo refleje.
