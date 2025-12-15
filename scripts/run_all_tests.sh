#!/usr/bin/env bash
set -euo pipefail

echo "=== ContinuuAI Full Test Suite ==="
echo "Running all integrity, security, and quality tests"
echo ""

# Track results
FAILED=()

run_test() {
    local name="$1"
    local script="$2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if python "$script"; then
        echo "✅ $name PASSED"
    else
        echo "❌ $name FAILED"
        FAILED+=("$name")
    fi
    echo ""
}

run_test "1. Provenance Invariants" "scripts/check_invariants.py"
run_test "2. ACL Negative Tests" "scripts/test_acl_negative.py"
run_test "3. MMR Property Tests" "scripts/test_mmr_properties.py"
run_test "4. Phrase Query Validation" "scripts/test_phrase_queries.py"
run_test "5. Recency Decay Validation" "scripts/test_recency_decay.py"
run_test "6. Synthetic Retrieval" "scripts/test_retrieval_synthetic.py"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== Test Suite Summary ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#FAILED[@]} -eq 0 ]; then
    echo "✅ All 6 test suites PASSED"
    echo ""
    echo "System integrity verified:"
    echo "  ✓ Greenfield reproducibility"
    echo "  ✓ Provenance accountability"
    echo "  ✓ Access control boundaries"
    echo "  ✓ MMR diversity/deduplication"
    echo "  ✓ Phrase query validation"
    echo "  ✓ Recency decay validation"
    exit 0
else
    echo "❌ ${#FAILED[@]}/6 test suites FAILED:"
    for test in "${FAILED[@]}"; do
        echo "  - $test"
    done
    exit 1
fi
