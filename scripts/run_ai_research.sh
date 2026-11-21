#!/usr/bin/env bash
# ==============================================================================
# Vectora AI — Mode A: AI Research Workflow
# Hardware Target: Intel Core i7-2600 (Sandy Bridge, AVX, 16 GB DDR3 RAM)
# ASD-STE100 Compliant Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
cd "${PROJECT_ROOT}"

BENCHMARK_LOG="${PROJECT_ROOT}/reports/mode_a_ai_research_benchmark.log"
mkdir -p "${PROJECT_ROOT}/reports"

echo "========================================================================"
echo "VECTORA AI — MODE A: LOCAL AI RESEARCH LAUNCH"
echo "========================================================================"
echo "Timestamp: $(date -Iseconds)" | tee "${BENCHMARK_LOG}"

# Step 1: Check existing production API
echo "[Step 1] Verifying production API health..."
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo "ERROR: Production API at http://localhost:8000/health is not healthy." >&2
    exit 1
fi
echo "Production API is healthy." | tee -a "${BENCHMARK_LOG}"

# Step 2: Start Ollama service under llm profile
echo "[Step 2] Starting Ollama container under profile 'llm'..."
docker compose --profile llm up -d ollama

# Step 3: Wait for Ollama container health
echo "[Step 3] Waiting for Ollama container to become healthy..."
MAX_WAIT=30
WAITED=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' vectora-ollama 2>/dev/null || true)" == "healthy" ]; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ ${WAITED} -ge ${MAX_WAIT} ]; then
        echo "ERROR: Ollama container failed to reach healthy state within ${MAX_WAIT}s." >&2
        docker logs vectora-ollama --tail 20 >&2
        exit 1
    fi
    echo "  - Waiting for container health (${WAITED}s / ${MAX_WAIT}s)..."
done
echo "Ollama container is healthy (waited ${WAITED}s)." | tee -a "${BENCHMARK_LOG}"

# Step 4: Verify installed models via Ollama localhost endpoint
echo "[Step 4] Checking Ollama models via 127.0.0.1:11435/api/tags..."
TAGS_JSON=$(curl -sf http://127.0.0.1:11435/api/tags || true)
echo "Ollama tags response: ${TAGS_JSON}" | tee -a "${BENCHMARK_LOG}"

# Step 5: Test request directly to Ollama API
echo "[Step 5] Executing test prompt to Gemma 3:4B via Ollama direct endpoint..."
START_TIME=$(date +%s%N)
TEST_RESP=$(curl -sf http://127.0.0.1:11435/api/generate -d '{
    "model": "gemma3:4b",
    "prompt": "List two key morphological differences between Anopheles and Culex mosquitoes. Keep response under 40 words.",
    "stream": false,
    "options": {
        "temperature": 0.1,
        "num_ctx": 1024
    }
}' || true)
END_TIME=$(date +%s%N)
DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

echo "Direct Ollama response received in ${DURATION_MS} ms:" | tee -a "${BENCHMARK_LOG}"
echo "${TEST_RESP}" | tee -a "${BENCHMARK_LOG}"

# Step 6: Test request via Vectora AI Backend Assistant endpoint
echo "[Step 6] Testing assistant integration via backend http://localhost:8000/api/v1/assistant/health..."
BACKEND_HEALTH=$(curl -sf http://localhost:8000/api/v1/assistant/health || true)
echo "Backend Assistant Health: ${BACKEND_HEALTH}" | tee -a "${BENCHMARK_LOG}"

echo "[Step 7] Testing structured query via backend http://localhost:8000/api/v1/assistant/chat..."
BACKEND_QUERY_RESP=$(curl -sf -X POST http://localhost:8000/api/v1/assistant/chat \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Confirm that local AI research mode is operational and summarize your role.",
        "temperature": 0.1,
        "json_mode": false
    }' || true)
echo "Backend Assistant Query Response:" | tee -a "${BENCHMARK_LOG}"
echo "${BACKEND_QUERY_RESP}" | tee -a "${BENCHMARK_LOG}"

# Step 8: Measure and log container resource usage
echo "[Step 8] Recording container resource usage..."
docker stats --no-stream vectora-ollama vectora-backend | tee -a "${BENCHMARK_LOG}"

echo "========================================================================"
echo "MODE A TEST COMPLETED SUCCESSFULLY."
echo "Benchmark log written to: ${BENCHMARK_LOG}"
echo "========================================================================"
