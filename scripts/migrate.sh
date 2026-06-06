#!/usr/bin/env bash
# ============================================================
# QuantFlow — Database Migration Helper
# Usage: ./scripts/migrate.sh [command]
# Commands:
#   up       — run all pending migrations (default)
#   down     — rollback one revision
#   revision — create a new empty migration
#   history  — show migration history
#   current  — show current revision
# ============================================================
set -euo pipefail

COMMAND="${1:-up}"
cd "$(dirname "$0")/.."

run_in_docker() {
    docker compose exec backend alembic "$@"
}

run_local() {
    cd backend && alembic "$@"
}

# Detect environment
if docker compose ps backend 2>/dev/null | grep -q "Up"; then
    RUNNER="docker"
else
    RUNNER="local"
fi

echo "🗄️  QuantFlow DB migrations ($RUNNER mode)"
echo "─────────────────────────────────────────"

case "$COMMAND" in
    up)
        echo "Running: alembic upgrade head"
        if [ "$RUNNER" = "docker" ]; then
            run_in_docker upgrade head
        else
            run_local upgrade head
        fi
        echo "✅ Migrations applied"
        ;;
    down)
        echo "Running: alembic downgrade -1"
        if [ "$RUNNER" = "docker" ]; then
            run_in_docker downgrade -1
        else
            run_local downgrade -1
        fi
        echo "✅ Rolled back one revision"
        ;;
    revision)
        MSG="${2:-auto}"
        echo "Creating revision: $MSG"
        if [ "$RUNNER" = "docker" ]; then
            run_in_docker revision --autogenerate -m "$MSG"
        else
            run_local revision --autogenerate -m "$MSG"
        fi
        ;;
    history)
        if [ "$RUNNER" = "docker" ]; then
            run_in_docker history
        else
            run_local history
        fi
        ;;
    current)
        if [ "$RUNNER" = "docker" ]; then
            run_in_docker current
        else
            run_local current
        fi
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Usage: $0 [up|down|revision|history|current]"
        exit 1
        ;;
esac
