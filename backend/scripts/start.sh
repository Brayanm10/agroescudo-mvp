#!/usr/bin/env sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ "${RUN_SEED_ON_START:-false}" = "true" ]; then
    echo "Running explicitly enabled pilot seed..."
    python -m app.seed
else
    echo "Skipping pilot seed (RUN_SEED_ON_START is not true)."
fi

echo "Starting AgroEscudo API..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
