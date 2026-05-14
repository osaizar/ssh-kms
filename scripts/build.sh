#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

if docker compose version >/dev/null 2>&1; then
    docker compose build
elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose build
else
    echo "Docker Compose is required." >&2
    exit 1
fi
