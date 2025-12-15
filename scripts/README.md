# Test Scripts Quick Reference

## Prerequisites
```bash
# Ensure services running
docker compose up -d postgres qdrant

# Install Python dependencies
pip install psycopg httpx numpy

# Apply migrations
cd services/retrieval && python migrate.py && cd ../..

# Start retrieval service
cd services/retrieval && uvicorn retrieval.main:app --port 8081 &
```

---

## Test Suites

### 1. Provenance Invariants
**What**: Validates every result has graph accountability  
**When**: After any retrieval or graph changes  
**Runtime**: ~2s

```bash
python scripts/check_invariants.py
# ✅ Invariants OK (graph provenance present)
# OR
# ❌ Invariant failed: spans without graph provenance: [...]
```

---

### 2. ACL Negative Tests
**What**: Proves access control boundaries hold  
**When**: After ACL/policy changes  
**Runtime**: ~5s

```bash
python scripts/test_acl_negative.py
# === ACL Negative Tests ===
# ✓ Fixtures created
# ✓ Test 1 PASSED: no scope → 0 results
# ✓ Test 2 PASSED: partial scope → only permitted artifacts
# ✓ Test 3 PASSED: seed matches exist but policy blocks all
# ✅ All 3 ACL tests PASSED
```

---

### 3. MMR Property Tests
**What**: Validates diversity/deduplication work  
**When**: After retrieval scoring changes  
**Runtime**: ~4s

```bash
python scripts/test_mmr_properties.py
# === MMR Property Tests ===
# === Test 1: Diversity Increases ===
# Greedy avg similarity: 0.342
# MMR avg similarity:    0.281
# ✓ MMR reduced avg similarity by 0.061
# 
# === Test 2: Deduplication Reduces Overlaps ===
# Greedy duplicates: 4
# MMR duplicates:    1
# ✓ MMR reduced duplicates by 3
#
# === Test 3: Top Result Quality Preserved ===
# Greedy top score: 0.8234
# MMR top score:    0.7891
# ✓ Quality preserved (degradation: 4.2%)
#
# ✅ All 3 MMR property tests PASSED
```

---

### 4. Synthetic Retrieval Test
**What**: End-to-end retrieval with synthetic data  
**When**: Smoke test after deployment  
**Runtime**: ~3s

```bash
python scripts/test_retrieval_synthetic.py
# Inserting synthetic evidence...
# Running retrieval query...
# ✓ Found 12 results
# ✓ Top result score: 0.8456
# ✓ Debug info present
# ✅ Retrieval test PASSED
```

---

## Run All Tests (Sequential)
```bash
#!/usr/bin/env bash
set -e

echo "=== Running Full Test Suite ==="

echo -e "\n1/4: Provenance Invariants"
python scripts/check_invariants.py

echo -e "\n2/4: ACL Negative Tests"
python scripts/test_acl_negative.py

echo -e "\n3/4: MMR Property Tests"
python scripts/test_mmr_properties.py

echo -e "\n4/4: Synthetic Retrieval"
python scripts/test_retrieval_synthetic.py

echo -e "\n✅ All Test Suites PASSED"
```

Save as `scripts/run_all_tests.sh`, make executable, run:
```bash
chmod +x scripts/run_all_tests.sh
./scripts/run_all_tests.sh
```

---

## Environment Variables

All scripts respect these env vars (with defaults):

```bash
export DATABASE_URL="postgres://continuuai:continuuai@localhost:5433/continuuai"
export RETRIEVAL_URL="http://localhost:8081/v1/retrieve"
export ORG_ID="00000000-0000-0000-0000-000000000000"
export PRINCIPAL_ID="d5f99e45-b729-4ac0-8101-c972acfd883b"
```

Override as needed for different environments.

---

## Troubleshooting

### "Connection refused" errors
```bash
# Verify services are up
docker compose ps
curl http://localhost:8081/v1/health
```

### "No results to validate"
```bash
# Insert synthetic evidence first
python scripts/insert_synthetic_evidence.py
# Then run graph-deriver
cd services/graph-deriver && python main.py && cd ../..
```

### "Invariant failed"
This is a **hard failure**—spans without provenance should never exist.
1. Check graph-deriver ran successfully
2. Verify span_node and edge_evidence tables populated
3. Review migration order (pgvector before vector columns)

### ACL tests fail
1. Verify migrations 0010-0011 applied (principal_role, role_scope)
2. Check test fixtures created successfully
3. Review retrieval service ACL enforcement logic

### MMR tests show no improvement
Could be valid if:
- Dataset naturally diverse (few duplicates)
- Query doesn't produce semantically similar results
- Not a failure if thresholds not met, just logged as warnings

---

## CI Integration

Tests run automatically in `.github/workflows/greenfield-ci.yml` on:
- Push to `main`
- Pull requests
- Manual workflow dispatch

Local scripts are **identical** to CI—no "works locally, breaks in CI" divergence.

---

## Adding New Tests

1. Create `scripts/test_<name>.py`
2. Follow pattern:
   - Async main with httpx for API calls
   - psycopg for DB queries
   - Exit 0 on pass, non-zero on fail
   - Print clear diagnostics
3. Make executable: `chmod +x scripts/test_<name>.py`
4. Add to `.github/workflows/greenfield-ci.yml`
5. Document in `docs/internal/TEST_SUITE.md`

---

**Quick Health Check** (30 seconds):
```bash
curl http://localhost:8081/v1/health && \
curl http://localhost:8081/v1/debug/weights | jq . && \
python scripts/check_invariants.py && \
echo "✅ System healthy"
```
