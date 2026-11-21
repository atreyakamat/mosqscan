#!/usr/bin/env bash
set -euo pipefail

# Vectora AI 2.2 — Server Start Script
# Intel Core i7-2600 AI Inference Host

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=========================================================="
echo " Starting Vectora AI 2.2 Server (Host: Intel Core i7-2600)"
echo "=========================================================="

# 1. Check Docker availability
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not in PATH." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running or current user lacks docker group permissions." >&2
    exit 1
fi

# 2. Verify ONNX Model Integrity
V3_MODEL="${REPO_ROOT}/models/vectora_v3_fp32.onnx"
EXPECTED_SHA256="c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa"

if [ ! -f "${V3_MODEL}" ]; then
    echo "ERROR: Required model artifact missing: ${V3_MODEL}" >&2
    exit 1
fi

echo "Verifying V3 FP32 model integrity..."
ACTUAL_SHA256=$(sha256sum "${V3_MODEL}" | awk '{print $1}')
if [ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]; then
    echo "ERROR: Model checksum mismatch!" >&2
    echo "  Expected: ${EXPECTED_SHA256}" >&2
    echo "  Actual:   ${ACTUAL_SHA256}" >&2
    exit 1
fi
echo "Model checksum verified: ${ACTUAL_SHA256:0:16}..."

# 3. Start services via Docker Compose
echo "Starting Docker Compose services..."
docker compose up -d

# 4. Wait for backend readiness
echo "Waiting for Vectora AI backend health check..."
MAX_ATTEMPTS=30
ATTEMPT=0
BACKEND_HEALTHY=0

while [ ${ATTEMPT} -lt ${MAX_ATTEMPTS} ]; do
    if curl -s -f http://127.0.0.1:8000/health >/dev/null 2>&1; then
        BACKEND_HEALTHY=1
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 1
done

if [ ${BACKEND_HEALTHY} -eq 1 ]; then
    # Detect primary local LAN IP
    LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -n1 || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    echo "----------------------------------------------------------"
    echo " SUCCESS: Vectora AI Server is healthy and running!"
    echo " Backend API:        http://127.0.0.1:8000"
    echo " Android LAN URL:    http://${LAN_IP}:8000"
    echo " Web Application:    http://127.0.0.1:3001 (or http://${LAN_IP}:3001)"
    echo " Model Status:       EXPERIMENTAL_NOT_FIELD_VALIDATED"
    echo " Inference Device:   Intel Core i7-2600 CPU (ONNX Runtime)"
    echo "----------------------------------------------------------"
else
    echo "ERROR: Backend failed to respond to /health within ${MAX_ATTEMPTS} seconds." >&2
    echo "Check container logs with: ./scripts/server-logs.sh backend" >&2
    exit 1
fi
