# LedgerLet in one image: the web app is built, then served by the API.
#
#   docker build -t ledgerlet .
#   docker run -p 10000:10000 --env-file .env ledgerlet
#
# Auth0's three VITE_ values are build arguments: Vite writes them into the built
# app. They're public (any visitor can read them), so this is safe. Render passes a
# service's environment variables as build arguments automatically.

# ---- 1. Build the web app ----
FROM node:22.20.0-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_AUTH0_DOMAIN
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_AUDIENCE
RUN npm run build

# ---- 2. The API, serving the web app ----
FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LEDGERLET_STATIC_DIR=/app/static
WORKDIR /app

# Exact versions from the lock, installed before the code so this layer is reused.
COPY requirements.lock ./
RUN pip install -r requirements.lock

COPY pyproject.toml alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/
RUN pip install --no-deps .
COPY --from=web /web/dist /app/static
COPY docker/start.sh /app/start.sh

# Never run as root.
RUN useradd --create-home --uid 10001 ledgerlet
USER ledgerlet

EXPOSE 10000
CMD ["/app/start.sh"]
