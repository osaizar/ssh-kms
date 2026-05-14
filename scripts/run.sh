#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${PROJECT_DIR}/config/ssh-keys.json}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

export CONFIG_FILE

cd "${PROJECT_DIR}"

if docker compose version >/dev/null 2>&1; then
    exec docker compose up
elif command -v docker-compose >/dev/null 2>&1; then
    exec docker-compose up
else
    echo "Docker Compose is required." >&2
    exit 1
fi
