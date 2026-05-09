#!/usr/bin/env bash
set -Eeuo pipefail

export PORT="${PORT:-8080}"
export NUXT_HOST="${NUXT_HOST:-127.0.0.1}"
export NUXT_PORT="${NUXT_PORT:-3000}"
export DJANGO_HOST="${DJANGO_HOST:-127.0.0.1}"
export DJANGO_PORT="${DJANGO_PORT:-8000}"
export BUILD_TARGET="${BUILD_TARGET:-production}"
export NODE_ENV="${NODE_ENV:-production}"
export JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}"
export NUXT_PUBLIC_API_URL="${NUXT_PUBLIC_API_URL:-}"
export NUXT_PUBLIC_APP_URL="${NUXT_PUBLIC_APP_URL:-${VIRTUAL_HOST:-}}"

if [[ -z "${VIRTUAL_HOST:-}" && -n "${APP_URL:-}" ]]; then
  export VIRTUAL_HOST="$APP_URL"
fi

missing=0
for name in JWT_SECRET VIRTUAL_HOST; do
  value="${!name:-}"
  if [[ -z "$value" ]]; then
    echo "Missing required environment variable: $name" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "Refusing to start production container with incomplete Django configuration." >&2
  exit 1
fi

export PYTHONPATH=/app/backend

envsubst '${PORT} ${NUXT_HOST} ${NUXT_PORT} ${DJANGO_HOST} ${DJANGO_PORT}' \
  < /etc/nginx/templates/app.conf.template \
  > /etc/nginx/conf.d/app.conf

pids=()

shutdown() {
  local status=${1:-0}
  trap - TERM INT EXIT
  if ((${#pids[@]} > 0)); then
    kill -TERM "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
  exit "$status"
}

trap 'shutdown 143' TERM INT
trap 'shutdown $?' EXIT

(
  cd /app/backend
  exec gunicorn wsgi:application \
    --bind "${DJANGO_HOST}:${DJANGO_PORT}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
) &
pids+=("$!")

(
  cd /app/frontend
  exec env \
    HOST="$NUXT_HOST" \
    PORT="$NUXT_PORT" \
    NITRO_HOST="$NUXT_HOST" \
    NITRO_PORT="$NUXT_PORT" \
    node /app/frontend/server/index.mjs
) &
pids+=("$!")

nginx -g 'daemon off;' &
pids+=("$!")

wait -n "${pids[@]}"
shutdown "$?"
