#!/usr/bin/env bash
# ==============================================================================
# Vectora AI — Mode B: Hybrid Model Training Script
# Hardware Target: Intel Core i7-2600 (Sandy Bridge, AVX, 16 GB DDR3 RAM)
# ASD-STE100 Compliant Implementation
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
cd "${PROJECT_ROOT}"

PYTHON_BIN="${PROJECT_ROOT}/vectora-ai-starter/.venv/bin/python"
LOG_DIR="${PROJECT_ROOT}/reports/research"
EXEC_LOG="${LOG_DIR}/hybrid_training_execution.log"
LATENCY_LOG="${LOG_DIR}/hybrid_training_server_latency.log"
PROD_MODEL="${PROJECT_ROOT}/models/vectora_v3_fp32.onnx"
EXPECTED_SHA256="c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa"

mkdir -p "${PROJECT_ROOT}/models/research" "${LOG_DIR}"

echo "========================================================================"
echo "VECTORA AI — MODE B: HYBRID TRAINING CONTROLLER"
echo "========================================================================"
echo "Timestamp: $(date -Iseconds)" | tee "${EXEC_LOG}"

# ------------------------------------------------------------------------------
# Step 1: Verify Production API Health
# ------------------------------------------------------------------------------
echo "[Step 1] Verifying production API health at http://localhost:8000/health..." | tee -a "${EXEC_LOG}"
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo "CRITICAL ERROR: Production API at http://localhost:8000/health is not healthy." | tee -a "${EXEC_LOG}" >&2
    exit 1
fi

HEALTH_JSON=$(curl -sf http://localhost:8000/api/v1/models/health || true)
echo "Production Model Health: ${HEALTH_JSON}" | tee -a "${EXEC_LOG}"

# ------------------------------------------------------------------------------
# Step 2: Record Baseline API Latency
# ------------------------------------------------------------------------------
echo "[Step 2] Recording baseline production API latency (20 samples)..." | tee -a "${EXEC_LOG}"
BASELINE_STATS=$("${PYTHON_BIN}" -c "
import urllib.request, time, statistics
lats = []
for _ in range(20):
    t0 = time.perf_counter()
    with urllib.request.urlopen('http://localhost:8000/api/v1/models/health', timeout=3.0) as resp:
        if resp.status == 200:
            lats.append((time.perf_counter() - t0) * 1000.0)
    time.sleep(0.05)
lats.sort()
median = statistics.median(lats)
mean = statistics.mean(lats)
p95 = lats[int(len(lats) * 0.95)]
print(f'Samples: {len(lats)} | Median: {median:.2f} ms | Mean: {mean:.2f} ms | P95: {p95:.2f} ms | Min: {min(lats):.2f} ms | Max: {max(lats):.2f} ms')
")
echo "Baseline Latency: ${BASELINE_STATS}" | tee -a "${EXEC_LOG}"

# ------------------------------------------------------------------------------
# Step 3: Stop Ollama Container (Unload Gemma to release CPU & RAM)
# ------------------------------------------------------------------------------
echo "[Step 3] Stopping Ollama container to release RAM and CPU for training..." | tee -a "${EXEC_LOG}"
docker compose stop ollama 2>&1 | tee -a "${EXEC_LOG}"
echo "Ollama container stopped successfully." | tee -a "${EXEC_LOG}"

# ------------------------------------------------------------------------------
# Step 4: Verify Available Memory
# ------------------------------------------------------------------------------
echo "[Step 4] Checking host available memory..." | tee -a "${EXEC_LOG}"
AVAIL_RAM_MB=$(free -m | awk '/^Mem:/{print $7}')
echo "Available RAM: ${AVAIL_RAM_MB} MB" | tee -a "${EXEC_LOG}"
if [ "${AVAIL_RAM_MB}" -lt 3000 ]; then
    echo "ERROR: Insufficient available memory (${AVAIL_RAM_MB} MB < 3000 MB required)." | tee -a "${EXEC_LOG}" >&2
    exit 1
fi

# Verify Production Model SHA-256 before training
PRE_SHA=$(sha256sum "${PROD_MODEL}" | awk '{print $1}')
echo "Pre-training Production Model SHA-256: ${PRE_SHA}" | tee -a "${EXEC_LOG}"
if [ "${PRE_SHA}" != "${EXPECTED_SHA256}" ]; then
    echo "ERROR: Production ONNX model hash does not match expected reference!" | tee -a "${EXEC_LOG}" >&2
    exit 1
fi

# ------------------------------------------------------------------------------
# Step 5 & 6: Launch Background Health Monitor & Execute Training
# ------------------------------------------------------------------------------
echo "[Step 5] Launching background production health monitor..." | tee -a "${EXEC_LOG}"
echo "timestamp,latency_ms,status" > "${LATENCY_LOG}"

MONITOR_STOP=0
monitor_loop() {
    while [ "${MONITOR_STOP}" -eq 0 ]; do
        t0=$(date +%s%N)
        if curl -sf --max-time 3 http://localhost:8000/api/v1/models/health > /dev/null; then
            t1=$(date +%s%N)
            dur_ms=$(( (t1 - t0) / 1000000 ))
            echo "$(date -Iseconds),${dur_ms},200" >> "${LATENCY_LOG}"
        else
            echo "$(date -Iseconds),-1,FAIL" >> "${LATENCY_LOG}"
        fi
        sleep 5
    done
}

monitor_loop &
MONITOR_PID=$!
echo "Health monitor started with PID ${MONITOR_PID}." | tee -a "${EXEC_LOG}"

cleanup() {
    echo "Terminating health monitor (PID ${MONITOR_PID})..."
    kill "${MONITOR_PID}" 2>/dev/null || true
    wait "${MONITOR_PID}" 2>/dev/null || true
}
trap cleanup EXIT

echo "[Step 6] Running hybrid classifier training script..." | tee -a "${EXEC_LOG}"
START_TRAIN_TIME=$(date +%s)

# Run hybrid classifier training with Primary (unweighted) and Ablation (class-weighted)
"${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/train_hybrid_classifier.py" \
    --epochs-head 1 \
    --epochs-fine 1 \
    --batch-size 4 \
    --threads 3 \
    --seed 42 \
    --run-ablation 2>&1 | tee -a "${EXEC_LOG}"

TRAIN_EXIT_CODE=${PIPESTATUS[0]}
END_TRAIN_TIME=$(date +%s)
TRAIN_ELAPSED=$(( END_TRAIN_TIME - START_TRAIN_TIME ))
echo "Training completed in ${TRAIN_ELAPSED} seconds with exit code ${TRAIN_EXIT_CODE}." | tee -a "${EXEC_LOG}"

if [ "${TRAIN_EXIT_CODE}" -ne 0 ]; then
    echo "ERROR: Training script exited with error code ${TRAIN_EXIT_CODE}." | tee -a "${EXEC_LOG}" >&2
    exit "${TRAIN_EXIT_CODE}"
fi

# Stop monitor
kill "${MONITOR_PID}" 2>/dev/null || true
trap - EXIT

# ------------------------------------------------------------------------------
# Step 7: Post-Training Verification
# ------------------------------------------------------------------------------
echo "[Step 7] Running post-training verification..." | tee -a "${EXEC_LOG}"

# Verify active server model integrity
POST_SHA=$(sha256sum "${PROD_MODEL}" | awk '{print $1}')
echo "Post-training Production Model SHA-256: ${POST_SHA}" | tee -a "${EXEC_LOG}"
if [ "${POST_SHA}" != "${EXPECTED_SHA256}" ]; then
    echo "CRITICAL VIOLATION: Production model was altered during training!" | tee -a "${EXEC_LOG}" >&2
    exit 1
fi
echo "Production model integrity confirmed: SHA-256 unmodified." | tee -a "${EXEC_LOG}"

# Measure post-training production latency
echo "Measuring post-training production API latency (20 samples)..." | tee -a "${EXEC_LOG}"
POST_STATS=$("${PYTHON_BIN}" -c "
import urllib.request, time, statistics
lats = []
for _ in range(20):
    t0 = time.perf_counter()
    with urllib.request.urlopen('http://localhost:8000/api/v1/models/health', timeout=3.0) as resp:
        if resp.status == 200:
            lats.append((time.perf_counter() - t0) * 1000.0)
    time.sleep(0.05)
lats.sort()
median = statistics.median(lats)
mean = statistics.mean(lats)
p95 = lats[int(len(lats) * 0.95)]
print(f'Samples: {len(lats)} | Median: {median:.2f} ms | Mean: {mean:.2f} ms | P95: {p95:.2f} ms | Min: {min(lats):.2f} ms | Max: {max(lats):.2f} ms')
")
echo "Post-training Latency: ${POST_STATS}" | tee -a "${EXEC_LOG}"

# Check latency logs collected during training
echo "Evaluating background latency measurements during training..." | tee -a "${EXEC_LOG}"
"${PYTHON_BIN}" -c "
import pandas as pd
df = pd.read_csv('${LATENCY_LOG}')
total = len(df)
failures = len(df[df['status'] != 200])
valid_lats = df[df['status'] == 200]['latency_ms']
if len(valid_lats) > 0:
    print(f'Server Health Checks During Training: {total} total, {failures} failures')
    print(f'Concurrent Latency: Median {valid_lats.median():.2f} ms | Mean {valid_lats.mean():.2f} ms | P95 {valid_lats.quantile(0.95):.2f} ms | Max {valid_lats.max():.2f} ms')
else:
    print('No valid health samples collected.')
" | tee -a "${EXEC_LOG}"

# Check Docker container statuses
echo "Active Docker Containers Status:" | tee -a "${EXEC_LOG}"
docker compose ps | tee -a "${EXEC_LOG}"

echo "========================================================================"
echo "MODE B: HYBRID TRAINING COMPLETED SUCCESSFULLY"
echo "Execution Log: ${EXEC_LOG}"
echo "Latency Log:   ${LATENCY_LOG}"
echo "========================================================================"
