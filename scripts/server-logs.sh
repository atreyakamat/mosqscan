#!/usr/bin/env bash
set -euo pipefail

# Vectora AI 2.2 — Server Logs Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

SERVICE="${1:-backend}"
LINES="${2:-100}"

echo "Tailing logs for service: ${SERVICE} (last ${LINES} lines)..."
docker compose logs -f --tail="${LINES}" "${SERVICE}"
