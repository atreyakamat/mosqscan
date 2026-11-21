#!/usr/bin/env bash
set -euo pipefail

# Vectora AI 2.2 — Server Status Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=========================================================="
echo " Vectora AI 2.2 — System Status & Resource Utilization"
echo "=========================================================="

echo "[1] Docker Compose Services:"
docker compose ps

echo ""
echo "[2] Resource Utilization (Docker Stats):"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" $(docker compose ps -q) 2>/dev/null || echo "Containers not running."

echo ""
echo "[3] Host Memory & CPU Status:"
free -h | grep -E "Mem:|Swap:"
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
