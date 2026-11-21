#!/usr/bin/env bash
set -euo pipefail

# Vectora AI 2.2 — Server Health Check Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=========================================================="
echo " Vectora AI 2.2 — Health Check"
echo "=========================================================="

# Check /health endpoint
HEALTH_URL="http://127.0.0.1:8000/health"
echo -n "Checking API health endpoint (${HEALTH_URL})... "
HTTP_STATUS=$(curl -s -o /tmp/vectora_health.json -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null || echo "000")

if [ "${HTTP_STATUS}" -eq 200 ]; then
    echo "OK (HTTP 200)"
    cat /tmp/vectora_health.json
    echo ""
else
    echo "FAILED (HTTP ${HTTP_STATUS})"
    exit 1
fi

# Check model manifest endpoint
MANIFEST_URL="http://127.0.0.1:8000/api/v1/models/info"
echo -n "Checking Model Info & Manifest (${MANIFEST_URL})... "
MANIFEST_STATUS=$(curl -s -o /tmp/vectora_manifest.json -w "%{http_code}" "${MANIFEST_URL}" 2>/dev/null || echo "000")
if [ "${MANIFEST_STATUS}" -eq 200 ]; then
    echo "OK (HTTP 200)"
else
    echo "WARNING (HTTP ${MANIFEST_STATUS})"
fi

# Model artifact on disk check
EXP_B_MODEL="${REPO_ROOT}/models/vectora_candidate_exp_b.onnx"
EXPECTED_SHA256="d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499"
if [ -f "${EXP_B_MODEL}" ]; then
    ACTUAL_SHA256=$(sha256sum "${EXP_B_MODEL}" | awk '{print $1}')
    if [ "${ACTUAL_SHA256}" = "${EXPECTED_SHA256}" ]; then
        echo "Exp B FP32 artifact: INTEGRITY VERIFIED (${ACTUAL_SHA256:0:16}...)"
    else
        echo "Exp B FP32 artifact: CHECKSUM CORRUPTED!" >&2
        exit 1
    fi
else
    echo "Exp B FP32 artifact: NOT FOUND" >&2
    exit 1
fi

LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -n1 || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
echo ""
echo "Connection addresses:"
echo "  Local:       http://127.0.0.1:8000"
echo "  Android LAN: http://${LAN_IP}:8000"
echo "All health checks passed successfully."
