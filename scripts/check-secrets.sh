#!/usr/bin/env bash
# Busca credenciales que se hayan colado en los archivos del repo.
# Uso:  pnpm run check:secrets   [archivo...]
#
# Red de seguridad para que no acabe una contrasena, un token o una clave
# privada dentro del repositorio.
# Compatible con el bash 3.2 que trae macOS (sin mapfile ni arrays asociativos).
set -uo pipefail

cd "$(dirname "$0")/.."

PATRONES=(
  'sk-ant-[A-Za-z0-9_-]{16,}'
  'sk-[A-Za-z0-9]{32,}'
  'AKIA[0-9A-Z]{16}'
  'gh[pousr]_[A-Za-z0-9]{20,}'
  'BEGIN [A-Z ]*PRIVATE KEY'
  '(ANTHROPIC_API_KEY|OPENAI_API_KEY|JWT_SECRET|POSTGRES_PASSWORD|SECRET_KEY)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9/+_.-]{12,}'
)

# Valores de ejemplo o de demo que no son secretos de verdad.
PERMITIDOS='cambia-esto|openssl rand|tu-clave|example|xxxx|\$\{|<[a-z-]+>|password123|demo1234|postgres:postgres|no-es-un-secreto|solo-para-ci|secrets\.[A-Z_]+'

listar_archivos() {
  if [ "$#" -gt 0 ]; then
    printf '%s\n' "$@"
  elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files
  else
    find . -type f \
      -not -path './node_modules/*' -not -path './*/node_modules/*' \
      -not -path './api/.venv/*' -not -path './web/dist/*' -not -path './.git/*'
  fi
}

HALLAZGOS=0

while IFS= read -r archivo; do
  [ -f "$archivo" ] || continue
  case "$archivo" in
    # El .env local guarda secretos a proposito y nunca se versiona; el hook
    # pre-commit se encarga de que no entre al repositorio.
    .env | ./.env | .env.local | ./.env.local | .env.example | ./.env.example)
      continue
      ;;
    scripts/check-secrets.sh | ./scripts/check-secrets.sh | .githooks/pre-commit | ./.githooks/pre-commit)
      continue
      ;;
    pnpm-lock.yaml | ./pnpm-lock.yaml | *.lock)
      continue
      ;;
  esac

  for patron in "${PATRONES[@]}"; do
    COINCIDENCIAS="$(grep -nEI "$patron" "$archivo" 2>/dev/null | grep -vE "$PERMITIDOS" || true)"
    if [ -n "$COINCIDENCIAS" ]; then
      printf '\033[31m%s\033[0m\n' "$archivo"
      printf '  %s\n' "$COINCIDENCIAS"
      HALLAZGOS=$((HALLAZGOS + 1))
      break  # con un patron confirmado basta para senalar el archivo
    fi
  done
done < <(listar_archivos "$@")

if [ "$HALLAZGOS" -gt 0 ]; then
  printf '\n\033[31mHay %s archivo(s) con posibles credenciales.\033[0m\n' "$HALLAZGOS"
  printf 'Saca el valor a una variable de entorno (.env) antes de hacer commit.\n'
  exit 1
fi

printf '\033[32mSin credenciales a la vista.\033[0m\n'
