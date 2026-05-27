#!/bin/sh
export POS_ERP_DATABASE_URL="postgresql://${POSTGRES_USER}:***@postgres:5432/${POSTGRES_DB}"
exec "$@"
