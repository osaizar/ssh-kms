#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "Docker Compose is required." >&2
    exit 1
fi

echo "Building backend test image..."
docker build \
    --target backend-test \
    -t ssh-kms-backend-test \
    "${PROJECT_DIR}"

echo "Running backend tests..."
docker run --rm ssh-kms-backend-test pytest /app/tests

echo "Building final Compose image..."
"${COMPOSE[@]}" build "$@"
