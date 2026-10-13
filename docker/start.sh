#!/bin/sh
# Bring the database up to date, then serve. Migrations are safe to run on every
# start: Alembic only applies the ones not yet applied.
set -e
alembic upgrade head
# Behind the host's proxy (Render): trust its X-Forwarded-* headers so request
# URLs are https and HMRC's fraud headers get the visitor's real IP.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
