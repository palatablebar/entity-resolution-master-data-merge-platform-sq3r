#!/bin/sh
set -e

echo "[entrypoint] $(date -Iseconds) bootstrap schema"
python -m scripts.init_db

echo "[entrypoint] $(date -Iseconds) starting uvicorn on :8000"
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
