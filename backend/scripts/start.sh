#!/usr/bin/env bash
set -euo pipefail

: "${VIONA_MODE:=api}"

echo "Starting Viona backend in mode: $VIONA_MODE"

if [[ "$VIONA_MODE" == "api" ]]; then
    # Uvicorn hanya menerima log-level lowercase (info, debug, warning, error, critical, trace).
    # ENV LOG_LEVEL bisa datang uppercase (INFO) dari .env / docker-compose.
    _log_level="$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"
    exec uvicorn app.api.app:application \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8000}" \
        --log-level "$_log_level"
elif [[ "$VIONA_MODE" == "agent" ]]; then
    # Pipecat dispatch server: receives LiveKit webhooks and spawns a bot per room.
    exec python -m app.agents.server
else
    echo "Unknown VIONA_MODE=$VIONA_MODE" >&2
    exit 1
fi

