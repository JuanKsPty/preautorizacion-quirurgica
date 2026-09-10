# Preautorizacion Quirurgica

Plantilla full stack lista para empezar a construir: **React + Vite** en el
frontend y una **API REST con FastAPI** en el backend, comunicandose por
HTTP/JSON. Un comando levanta todo.

## Que trae ya montado

- **Autenticacion completa**: registro, login y sesion con JWT, contrasenas con
  hash Argon2 y rutas protegidas en el frontend.
- **CRUD de ejemplo** cableado punta a punta (modelo, endpoints, servicio,
  formulario validado, estados de carga/vacio/error) para copiar como plantilla.
- **Chat con IA en streaming**: endpoint SSE con el SDK de Anthropic y un hook
  `useChat` que muestra la respuesta token por token.
- **Health check en vivo** en la pantalla de inicio: demuestra de un vistazo que
  el frontend y la API se estan hablando.
- **PostgreSQL** en contenedor, con recarga en caliente en frontend y backend.
- Tema claro/oscuro, componentes de shadcn/ui, pruebas, linter y CI.

## Tecnologias

| Capa | Herramientas |
| --- | --- |
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS 4, shadcn/ui, React Router 8, TanStack Query |
| Backend | Python 3.13, FastAPI, SQLModel, Pydantic, JWT (PyJWT), Argon2 (pwdlib) |
| Base de datos | PostgreSQL 18 (funciona igual con SQLite) |
| IA | SDK oficial de Anthropic, respuesta en streaming (SSE) |
| Herramientas | pnpm, uv, Docker Compose, Vitest, pytest, ruff, oxlint |

## Instalacion y ejecucion

### Requisitos

| Herramienta | Version | Para que |
| --- | --- | --- |
| [Docker](https://www.docker.com/products/docker-desktop/) | Compose v2 | levanta la aplicacion completa |
| [Node.js](https://nodejs.org) | 22.22 o superior (probado en 24) | autocompletado del editor y pruebas |
| [pnpm](https://pnpm.io/installation) | 10 o superior | dependencias del frontend |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.9 o superior | dependencias de Python |

No hace falta instalar Python ni PostgreSQL a mano: los contenedores traen las
versiones correctas y `uv` baja el interprete para las pruebas locales.

### Puesta en marcha

```bash
git clone <URL-DEL-REPOSITORIO>
cd <carpeta-del-proyecto>

pnpm run setup     # un solo comando: .env, dependencias, contenedores y datos demo
```

Al terminar ya esta todo corriendo:

| Servicio | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/health |
| Documentacion de la API | http://localhost:8000/api/docs |
| PostgreSQL | localhost:5432 |

Usuario de demostracion: **demo@demo.com** / **demo1234**

`pnpm run setup` levanta tres contenedores con **docker compose**: `web` (Vite),
`api` (FastAPI) y `db` (PostgreSQL). El codigo esta montado como volumen, asi que
**al guardar un archivo se recarga solo**, sin reconstruir nada.

```bash
pnpm dev           # los mismos contenedores, con los logs en vivo (Ctrl+C sale)
pnpm stop          # apagar
pnpm run logs      # seguir los logs sin bloquear la terminal
pnpm run ps        # que esta corriendo
```

> `pnpm run setup` (con `run`) y no `pnpm setup`: `setup` a secas es un comando
> propio de pnpm y hace otra cosa.

**Reparto de responsabilidades:** la aplicacion vive en los contenedores; las
pruebas, el linter y el autocompletado corren en tu maquina (`pnpm test`,
`pnpm lint`) y no necesitan Docker.

Si cambias dependencias (`package.json` o `pyproject.toml`), reconstruye:
`pnpm run dev:build`.

Para usar el chat con IA, pon tu clave en el `.env` de la raiz:
`ANTHROPIC_API_KEY=sk-ant-...` y reinicia (`pnpm stop && pnpm dev`). Sin clave, el
resto de la aplicacion funciona igual y ese endpoint responde con un mensaje claro.

### Ejecucion sin Docker

Si no tienes Docker (o quieres los procesos directamente en la maquina), cambia
una linea del `.env` para usar SQLite:

```env
# DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/app
DATABASE_URL=sqlite:///./app.db
```

```bash
pnpm install && uv sync --directory api
pnpm run seed:host      # datos de demo
pnpm run dev:host       # frontend y API como procesos locales
```

Tambien sirve la mezcla: `pnpm run db:up` levanta solo PostgreSQL en un
contenedor y `pnpm run dev:host` corre el resto en la maquina.

### Version desplegada (nginx)

Para dejarlo corriendo como en produccion: el frontend se compila y lo sirve
nginx, que ademas proxea `/api` hacia el contenedor de la API.

```bash
pnpm run docker:prod    # ->  http://localhost:8080
```

### Comandos disponibles

| Comando | Que hace |
| --- | --- |
| `pnpm run setup` | Deja todo listo y corriendo desde cero |
| `pnpm dev` | Los contenedores con los logs en vivo |
| `pnpm run dev:build` | Igual, reconstruyendo las imagenes (tras cambiar dependencias) |
| `pnpm stop` | Apaga los contenedores |
| `pnpm run logs` / `logs:api` / `logs:web` | Sigue los logs |
| `pnpm run seed` | Carga usuario y datos de demostracion (idempotente) |
| `pnpm test` | Pruebas de la API (pytest) y del frontend (Vitest), sin Docker |
| `pnpm lint` | oxlint en el frontend, ruff en la API |
| `pnpm run typecheck` | Comprobacion de tipos de TypeScript |
| `pnpm run format` | Prettier + ruff format |
| `pnpm run check:secrets` | Busca credenciales filtradas en el repo |
| `pnpm run db:psql` | Consola SQL de la base |
| `pnpm run db:reset` | Borra la base y la vuelve a levantar vacia |
| `pnpm run db:revision "msg"` / `db:migrate` | Migraciones con Alembic |
| `pnpm run shell:api` | Una terminal dentro del contenedor de la API |
| `pnpm run docker:prod` | La version compilada servida por nginx (:8080) |
| `pnpm run dev:host` | Frontend y API como procesos locales, sin contenedores |

## La API

Todo cuelga de `/api` y esta documentado y probable desde
[`/api/docs`](http://localhost:8000/api/docs) (Swagger UI, generado por FastAPI).

| Metodo | Ruta | Que hace |
| --- | --- | --- |
| `GET` | `/api/health` | Estado de la API, de la base y si la IA esta habilitada |
| `POST` | `/api/auth/register` | Crea cuenta y devuelve el token |
| `POST` | `/api/auth/login` | Inicia sesion |
| `GET` | `/api/auth/me` | Usuario de la sesion actual |
| `GET` | `/api/items` | Lista los items del usuario |
| `POST` | `/api/items` | Crea un item |
| `PATCH` | `/api/items/{id}` | Actualiza un item |
| `DELETE` | `/api/items/{id}` | Borra un item |
| `POST` | `/api/chat` | Respuesta del modelo en streaming (SSE) |

Los endpoints protegidos esperan el header `Authorization: Bearer <token>`.

## Estructura del proyecto

```
.
├── web/                     Frontend (React + Vite)
│   └── src/
│       ├── pages/           Una pantalla por archivo
│       ├── components/      ui/ = shadcn, layout/ = cascara de la app
│       ├── hooks/           useAuth, useChat
│       ├── services/        Unico sitio que habla con la API
│       ├── types/api.ts     DTOs de la API y modelos de dominio
│       └── lib/             env, utils, identidad del proyecto
├── api/                     Backend (FastAPI)
│   ├── app/
│   │   ├── api/routes/      health, auth, items, chat
│   │   ├── core/            config, security, dependencias
│   │   ├── models/          Tablas y esquemas (SQLModel)
│   │   ├── db/session.py    Motor y sesion
│   │   ├── seed.py          Datos de demostracion
│   │   └── main.py          Arranque de la aplicacion
│   ├── alembic/             Migraciones (inertes hasta que hagan falta)
│   └── tests/               pytest sobre SQLite en memoria
├── scripts/                 setup, new-project, check-secrets
├── .env.example             Unica fuente de variables de entorno
├── docker-compose.yml       Desarrollo: web + api + db con recarga en caliente
└── docker-compose.prod.yml  Version desplegada: build estatico tras nginx
```

Decisiones tecnicas y convenciones: [`CLAUDE.md`](CLAUDE.md).

## Adaptar la plantilla a tu proyecto

1. **Renombra la entidad de ejemplo.** `item` aparece en cinco sitios:
   `api/app/models/item.py`, `api/app/api/routes/items.py`,
   `web/src/services/itemsService.ts`, `web/src/pages/ItemsPage.tsx` y
   `web/src/types/api.ts`. Copia ese patron para la entidad real
   (producto, pedido, reporte...).
2. **Si no vas a usar el chat IA**, borra `api/app/api/routes/chat.py`,
   `web/src/pages/ChatPage.tsx`, `web/src/hooks/useChat.ts`,
   `web/src/services/chatService.ts` y sus referencias en `api/app/api/router.py`,
   `web/src/App.tsx` y `web/src/components/layout/Navbar.tsx`.
3. **Cambia el nombre visible** en `web/src/lib/project.ts`.
4. Si el proyecto **no necesita usuarios**, quita `CurrentUser` de las rutas y
   `ProtectedRoute` del router: el CRUD sigue funcionando.

## Empezar un proyecto nuevo desde esta plantilla

```bash
bash scripts/new-project.sh <nombre> [destino] [--github owner/repo] [--collab usuario]
```

Copia la plantilla sin `node_modules` ni `.git`, renombra el proyecto en todos
los archivos, genera un `.env` con un `JWT_SECRET` nuevo, configura los hooks de
git y hace el commit inicial. Con `--github` ademas crea el repositorio y lo
sube; con `--collab` invita a un colaborador.

## Seguridad

- El `.env` nunca se versiona (esta en `.gitignore`) y hay un hook `pre-commit`
  que bloquea el commit si detecta un `.env` o un patron de clave.
- `pnpm run check:secrets` escanea el repositorio a mano cuando quieras.
- Las contrasenas se guardan con hash Argon2; la API nunca devuelve el hash.

## Licencia

MIT. Ver [LICENSE](LICENSE).
