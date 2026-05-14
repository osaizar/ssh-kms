#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-ssh-kms:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-ssh-kms}"
HOST_PORT="${HOST_PORT:-5000}"
CONTAINER_PORT="${CONTAINER_PORT:-5000}"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/ssh-keys.json}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

exec docker run --rm -it \
    --name "${CONTAINER_NAME}" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    -v "${CONFIG_FILE}:/config/ssh-keys.json:rw" \
    "${IMAGE_NAME}"
