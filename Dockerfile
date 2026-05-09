# syntax=docker/dockerfile:1

# Build Nuxt frontend from the existing frontend package.
FROM node:20-alpine AS frontend-builder
WORKDIR /app
RUN npm install -g pnpm@9
COPY frontend/.npmrc frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

# Runtime image for Timeweb App Platform Dockerfile deployment.
# One public listener is nginx on $PORT/8080; Nuxt and Django stay internal.
FROM node:20-bookworm-slim AS runtime

ENV NODE_ENV=production \
    BUILD_TARGET=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    NUXT_HOST=127.0.0.1 \
    NUXT_PORT=3000 \
    DJANGO_HOST=127.0.0.1 \
    DJANGO_PORT=8000 \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        gettext-base \
        nginx \
        python3 \
        python3-pip \
        python3-venv \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

WORKDIR /app

COPY backends/python/api/requirements.txt /tmp/python-requirements.txt
RUN pip install --no-cache-dir -r /tmp/python-requirements.txt \
    && rm -f /tmp/python-requirements.txt

COPY backends/python/api/ /app/backend/
COPY --from=frontend-builder /app/.output/ /app/frontend/
COPY deploy/timeweb/nginx.conf.template /etc/nginx/templates/app.conf.template
COPY deploy/timeweb/entrypoint.sh /usr/local/bin/timeweb-entrypoint.sh

RUN chmod +x /usr/local/bin/timeweb-entrypoint.sh \
    && rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf \
    && mkdir -p /run/nginx /var/cache/nginx/client_temp

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/nginx-health" >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/timeweb-entrypoint.sh"]
