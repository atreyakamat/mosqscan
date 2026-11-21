#!/bin/bash
# verify_checksums.sh
# Verifies ONNX model checksums match the manifest.
# Run from the model-registry/ directory or any location; paths are relative to this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../vectora-ai-starter/models"

FP32_FILE="efficientnet_b0.onnx"
INT8_FILE="efficientnet_b0_int8.onnx"

FP32_EXPECTED="03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19"
INT8_EXPECTED="bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95"

PASS=0
FAIL=0

check_file() {
    local label="$1"
    local filepath="$2"
    local expected="$3"

    if [ ! -f "$filepath" ]; then
        echo "  [MISSING]  $label — file not found: $filepath"
        FAIL=$((FAIL + 1))
        return
    fi

    local actual
    actual=$(sha256sum "$filepath" | awk '{print $1}')

    if [ "$actual" = "$expected" ]; then
        echo "  [OK]       $label"
        echo "             SHA-256: $actual"
        PASS=$((PASS + 1))
    else
        echo "  [MISMATCH] $label"
        echo "             Expected: $expected"
        echo "             Actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

echo "============================================================"
echo " Vectora AI — ONNX Model Checksum Verification"
echo " Model directory: $MODEL_DIR"
echo "============================================================"
echo ""

check_file "FP32 backend model  ($FP32_FILE)" "$MODEL_DIR/$FP32_FILE" "$FP32_EXPECTED"
echo ""
check_file "INT8 Android model  ($INT8_FILE)" "$MODEL_DIR/$INT8_FILE" "$INT8_EXPECTED"

echo ""
echo "------------------------------------------------------------"
echo " Results: $PASS passed, $FAIL failed"
echo "------------------------------------------------------------"

if [ "$FAIL" -gt 0 ]; then
    echo " ❌ Checksum verification FAILED. Do not deploy these models."
    exit 1
else
    echo " ✅ All checksums verified. Models are intact."
    exit 0
fi
