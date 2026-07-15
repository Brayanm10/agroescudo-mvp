#!/usr/bin/env sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Running pilot seed..."
python -m app.seed

echo "Starting AgroEscudo API..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
