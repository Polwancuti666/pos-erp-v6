#!/bin/sh
# Build DATABASE_URL from individual env vars if not set directly
if [ -z "$POS_ERP_DATABASE_URL" ]; then
    DB_USER="${POSTGRES_USER:-erp}"
    DB_PASS="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
    DB_HOST="${POSTGRES_HOST:-postgres}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_NAME="${POSTGRES_DB:-pos_erp}"
    export POS_ERP_DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

exec "$@"
