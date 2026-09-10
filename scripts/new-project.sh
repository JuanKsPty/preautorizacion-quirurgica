#!/usr/bin/env bash
# Crea un proyecto nuevo a partir de esta plantilla.
#
#   bash scripts/new-project.sh <nombre> [destino] [--github owner/repo] [--collab usuario]
#
# Ejemplos:
#   bash scripts/new-project.sh reto-emprende-2026
#   bash scripts/new-project.sh gong-cha-cup ~/dev/gong-cha --github juank/gong-cha-cup --collab compañero
set -euo pipefail

PLANTILLA="$(cd "$(dirname "$0")/.." && pwd)"

azul() { printf '\033[36m%s\033[0m\n' "$1"; }
ok() { printf '\033[32m  ok\033[0m %s\n' "$1"; }
error() {
  printf '\033[31mError:\033[0m %s\n' "$1" >&2
  exit 1
}

NOMBRE="${1:-}"
[ -n "$NOMBRE" ] || error "falta el nombre. Uso: bash scripts/new-project.sh <nombre> [destino]"
shift

case "$NOMBRE" in
  -*) error "el nombre no puede empezar con guion" ;;
  *[!a-zA-Z0-9-_]*) error "usa solo letras, numeros, guiones y guiones bajos en el nombre" ;;
esac

DESTINO=""
REPO_GITHUB=""
COLABORADOR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --github)
      REPO_GITHUB="${2:-}"
      shift 2
      ;;
    --collab)
      COLABORADOR="${2:-}"
      shift 2
      ;;
    -*) error "opcion desconocida: $1" ;;
    *)
      DESTINO="$1"
      shift
      ;;
  esac
done

[ -n "$DESTINO" ] || DESTINO="$(dirname "$PLANTILLA")/$NOMBRE"
[ -e "$DESTINO" ] && error "$DESTINO ya existe"

azul "1/5  Copiando la plantilla a $DESTINO"
mkdir -p "$DESTINO"
rsync -a \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude 'dist/' \
  --exclude '.env' \
  --exclude '*.db' \
  --exclude '.DS_Store' \
  "$PLANTILLA"/ "$DESTINO"/
ok 'archivos copiados'

azul '2/5  Renombrando el proyecto'
cd "$DESTINO"
NOMBRE="$NOMBRE" python3 - <<'PY'
import json
import os
import pathlib
import re

nombre = os.environ['NOMBRE']
titulo = nombre.replace('-', ' ').replace('_', ' ').title()

# package.json de la raiz
p = pathlib.Path('package.json')
datos = json.loads(p.read_text())
datos['name'] = nombre
datos['description'] = f'{titulo} - React + Vite + FastAPI'
p.write_text(json.dumps(datos, indent=2) + '\n')

# nombre del proyecto de compose (los dos archivos deben coincidir)
for archivo in ('docker-compose.yml', 'docker-compose.prod.yml'):
    p = pathlib.Path(archivo)
    texto = re.sub(r'^name: .*$', f'name: {nombre}', p.read_text(), count=1, flags=re.M)
    # Las imagenes tambien llevan el nombre del proyecto, para que dos
    # hackathones distintos no se pisen las etiquetas.
    texto = re.sub(r'^(\s*image: )hackathon-', rf'\1{nombre}-', texto, flags=re.M)
    p.write_text(texto)

# identidad que muestra el frontend
p = pathlib.Path('web/src/lib/project.ts')
texto = p.read_text()
texto = texto.replace("name: 'Hackathon Starter'", f"name: '{titulo}'")
p.write_text(texto)

# titulo de la pestana
p = pathlib.Path('web/index.html')
p.write_text(p.read_text().replace('<title>Hackathon Starter</title>', f'<title>{titulo}</title>'))

# titulo del README
p = pathlib.Path('README.md')
lineas = p.read_text().splitlines(keepends=True)
if lineas and lineas[0].startswith('# '):
    lineas[0] = f'# {titulo}\n'
p.write_text(''.join(lineas))

print(f'  proyecto: {nombre}  |  titulo visible: {titulo}')
PY
ok 'nombre aplicado'

azul '3/5  Archivo .env'
cp .env.example .env
if command -v openssl >/dev/null 2>&1; then
  SECRETO="$(openssl rand -hex 32)" python3 - <<'PY'
import os
import pathlib
import re

p = pathlib.Path('.env')
p.write_text(
    re.sub(r'^JWT_SECRET=.*$', f"JWT_SECRET={os.environ['SECRETO']}", p.read_text(), flags=re.M)
)
PY
  ok '.env con JWT_SECRET propio'
else
  ok '.env creado (cambia JWT_SECRET a mano)'
fi

azul '4/5  Repositorio git'
git init -q -b main
git config commit.template .gitmessage
git config core.hooksPath .githooks
git add -A
git -c user.useConfigOnly=false commit -q -m "chore: bootstrap desde la plantilla base

Punto de partida: plantilla React + Vite + FastAPI.
El desarrollo propio del proyecto empieza en este commit.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
ok 'commit inicial hecho (hooks y plantilla de commit configurados)'

if [ -n "$REPO_GITHUB" ]; then
  azul '5/5  GitHub'
  if ! command -v gh >/dev/null 2>&1; then
    printf '  gh no esta instalado; sube el repo a mano.\n'
  else
    gh repo create "$REPO_GITHUB" --public --source . --remote origin --push
    ok "repo creado: $REPO_GITHUB"
    if [ -n "$COLABORADOR" ]; then
      gh api -X PUT "repos/$REPO_GITHUB/collaborators/$COLABORADOR" -f permission=push >/dev/null
      ok "invitacion enviada a $COLABORADOR"
    fi
  fi
else
  azul '5/5  GitHub (omitido)'
  printf '  cuando quieras: gh repo create <owner/repo> --public --source . --remote origin --push\n'
  printf '  y agrega a quien vaya a colaborar contigo.\n'
fi

printf '\n\033[32mProyecto listo.\033[0m Siguiente:\n'
printf '  cd %s\n' "$DESTINO"
printf '  pnpm run setup && pnpm dev\n\n'
printf 'Siguiente paso: adapta el README y renombra la entidad de ejemplo.\n'
