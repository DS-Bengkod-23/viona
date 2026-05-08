#!/usr/bin/env bash
set -euo pipefail

: "${VIONA_MODE:=api}"

echo "Starting Viona backend in mode: $VIONA_MODE"

if [[ "$VIONA_MODE" == "api" ]]; then
    exec uvicorn app.api.app:application \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8000}" \
        --log-level "${LOG_LEVEL:-info}"
elif [[ "$VIONA_MODE" == "agent" ]]; then
    exec python -m app.agents.worker start
else
    echo "Unknown VIONA_MODE=$VIONA_MODE" >&2
    exit 1
fi
