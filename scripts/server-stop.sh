#!/usr/bin/env bash
set -euo pipefail

# Vectora AI 2.2 — Server Stop Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "Stopping Vectora AI Docker services..."
docker compose stop

echo "Services stopped. (To remove containers entirely, run 'docker compose down')"
