#!/usr/bin/env bash
# Prepara el proyecto desde cero. Uso:  pnpm run setup
#
# Deja todo corriendo en contenedores (frontend, API y Postgres) y con datos
# de demostracion cargados.
set -euo pipefail

cd "$(dirname "$0")/.."

azul() { printf '\033[36m%s\033[0m\n' "$1"; }
ok() { printf '\033[32m  ok\033[0m %s\n' "$1"; }
aviso() { printf '\033[33m  !\033[0m %s\n' "$1"; }

# ---------------------------------------------------------------- 1. entorno
azul '1/4  Archivo .env'
if [ -f .env ]; then
  ok '.env ya existia, no lo toco'
else
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
    ok '.env creado con un JWT_SECRET nuevo'
  else
    aviso '.env creado, pero cambia JWT_SECRET a mano (no encontre openssl)'
  fi
  aviso 'si vas a usar el chat IA, pon tu ANTHROPIC_API_KEY en .env'
fi

# ------------------------------------------------- 2. dependencias del editor
azul '2/4  Dependencias en la maquina (para el editor, los tests y el linter)'
pnpm install
uv sync --directory api
ok 'autocompletado y pnpm test listos'

# --------------------------------------------------------------- 3. Docker
azul '3/4  Contenedores'
if ! docker info >/dev/null 2>&1; then
  aviso 'Docker no responde. Abre Docker Desktop y vuelve a correr: pnpm run setup'
  aviso 'Mientras tanto puedes trabajar sin Docker:'
  aviso '  1. en .env pon  DATABASE_URL=sqlite:///./app.db'
  aviso '  2. pnpm run seed:host'
  aviso '  3. pnpm run dev:host'
  exit 1
fi

printf '     construyendo y levantando db + api + web (la primera vez tarda)\n'
docker compose up -d --build
ok 'contenedores arriba'

# ------------------------------------------------------- 4. esperar y sembrar
azul '4/4  Datos de demostracion'
printf '     esperando a que la API responda'
LISTA=no
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null http://127.0.0.1:8000/api/health; then
    LISTA=si
    break
  fi
  printf '.'
  sleep 1
done
printf '\n'

if [ "$LISTA" = no ]; then
  aviso 'la API no respondio a tiempo. Mira que paso con:  pnpm run logs'
  exit 1
fi
ok 'API respondiendo'

docker compose exec -T api python -m app.seed
ok 'datos de demo cargados'

printf '\n\033[32mListo.\033[0m Todo esta corriendo ya:\n'
printf '  frontend  http://localhost:5173\n'
printf '  API       http://localhost:8000/api/docs\n'
printf '  usuario   demo@demo.com / demo1234\n\n'
printf 'Comandos del dia a dia:\n'
printf '  pnpm dev     ver los logs en vivo (Ctrl+C para salir)\n'
printf '  pnpm stop    apagar los contenedores\n'
printf '  pnpm test    pruebas (no necesita contenedores)\n'
