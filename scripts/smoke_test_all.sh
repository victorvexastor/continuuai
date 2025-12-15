#!/usr/bin/env bash
set -euo pipefail

echo "=== ContinuuAI Full Stack Smoke Test ==="
echo "Verifying all services, endpoints, and test suites"
echo ""

FAILED=()

check() {
    local name="$1"
    local cmd="$2"
    echo -n "  Testing $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅"
    else
        echo "❌"
        FAILED+=("$name")
    fi
}

echo "━━━ Phase 1: Infrastructure ━━━"
check "Postgres running" "docker ps | grep -q postgres"
check "Qdrant running" "docker ps | grep -q qdrant"

echo ""
echo "━━━ Phase 2: Service Endpoints ━━━"
check "Retrieval /health" "curl -sf http://localhost:8081/v1/health"
check "Retrieval /debug/weights" "curl -sf http://localhost:8081/v1/debug/weights"
check "Retrieval /debug/sql" "curl -sf http://localhost:8081/v1/debug/sql || test $? -eq 22"  # 403 is OK

echo ""
echo "━━━ Phase 3: Database Schema ━━━"
check "evidence_span table" "docker exec \$(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c 'SELECT COUNT(*) FROM evidence_span' -t"
check "span_node table" "docker exec \$(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c 'SELECT COUNT(*) FROM span_node' -t"
check "graph_edge table" "docker exec \$(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c 'SELECT COUNT(*) FROM graph_edge' -t"
check "schema_migrations" "docker exec \$(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c 'SELECT COUNT(*) FROM schema_migrations' -t"

echo ""
echo "━━━ Phase 4: Test Scripts Exist ━━━"
check "check_invariants.py" "test -x scripts/check_invariants.py"
check "test_acl_negative.py" "test -x scripts/test_acl_negative.py"
check "test_mmr_properties.py" "test -x scripts/test_mmr_properties.py"
check "test_phrase_queries.py" "test -x scripts/test_phrase_queries.py"
check "test_recency_decay.py" "test -x scripts/test_recency_decay.py"
check "run_all_tests.sh" "test -x scripts/run_all_tests.sh"

echo ""
echo "━━━ Phase 5: Documentation ━━━"
check "TEST_SUITE.md" "test -f docs/internal/TEST_SUITE.md"
check "IMPLEMENTATION_COMPLETE.md" "test -f IMPLEMENTATION_COMPLETE.md"
check "scripts/README.md" "test -f scripts/README.md"
check "Greenfield CI workflow" "test -f .github/workflows/greenfield-ci.yml"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "✅ All smoke tests PASSED"
    echo ""
    echo "Stack is operational:"
    echo "  ✓ Infrastructure running"
    echo "  ✓ Service endpoints responding"
    echo "  ✓ Database schema present"
    echo "  ✓ Test scripts ready"
    echo "  ✓ Documentation complete"
    echo ""
    echo "Ready to run: ./scripts/run_all_tests.sh"
    exit 0
else
    echo "❌ ${#FAILED[@]} smoke tests FAILED:"
    for test in "${FAILED[@]}"; do
        echo "  - $test"
    done
    exit 1
fi
