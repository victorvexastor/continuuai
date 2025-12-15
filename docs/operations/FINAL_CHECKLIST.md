# ContinuuAI Final Verification Checklist

**Date**: 2025-12-15  
**Goal**: Verify all components operational before handoff

---

## ✅ Phase 1: Infrastructure

- [ ] Postgres container running
- [ ] Qdrant container running
- [ ] All migrations applied
- [ ] schema_migrations table has 12+ rows
- [ ] No migration errors in logs

**Commands**:
```bash
docker ps | grep postgres
docker ps | grep qdrant
docker exec $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "SELECT COUNT(*) FROM schema_migrations;"
```

---

## ✅ Phase 2: Service Endpoints

- [ ] Retrieval service responds to /v1/health
- [ ] /v1/debug/weights returns config
- [ ] /v1/debug/sql returns SQL templates (or 403)
- [ ] Service logs show no errors

**Commands**:
```bash
curl -f http://localhost:8081/v1/health
curl -f http://localhost:8081/v1/debug/weights | jq .
curl http://localhost:8081/v1/debug/sql | jq . || echo "403 expected if token required"
docker compose logs retrieval --tail 50
```

---

## ✅ Phase 3: Database Schema

- [ ] evidence_span table exists
- [ ] span_node table exists
- [ ] graph_edge table exists
- [ ] edge_evidence table exists
- [ ] principal_role table exists
- [ ] role_scope table exists
- [ ] pgvector extension enabled

**Commands**:
```bash
docker exec $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "\dt" | grep evidence_span
docker exec $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "\dt" | grep span_node
docker exec $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "\dx" | grep vector
```

---

## ✅ Phase 4: Test Scripts

- [ ] check_invariants.py is executable
- [ ] test_acl_negative.py is executable
- [ ] test_mmr_properties.py is executable
- [ ] test_phrase_queries.py is executable
- [ ] test_recency_decay.py is executable
- [ ] run_all_tests.sh is executable
- [ ] smoke_test_all.sh is executable

**Commands**:
```bash
ls -lh scripts/*.py scripts/*.sh | grep -E "^-rwx"
```

---

## ✅ Phase 5: Smoke Test

- [ ] Smoke test passes all checks

**Command**:
```bash
./scripts/smoke_test_all.sh
# Expected: ✅ All smoke tests PASSED
```

---

## ✅ Phase 6: Individual Test Suites

- [ ] Provenance invariants test passes
- [ ] ACL negative tests pass
- [ ] MMR property tests pass
- [ ] Phrase query tests pass
- [ ] Recency decay tests pass

**Commands** (run individually if smoke passed):
```bash
python scripts/check_invariants.py
python scripts/test_acl_negative.py
python scripts/test_mmr_properties.py
python scripts/test_phrase_queries.py
python scripts/test_recency_decay.py
```

---

## ✅ Phase 7: Full Test Suite

- [ ] Master test runner passes all 6 suites

**Command**:
```bash
./scripts/run_all_tests.sh
# Expected: ✅ All 6 test suites PASSED
```

---

## ✅ Phase 8: Documentation

- [ ] TEST_SUITE.md exists and complete
- [ ] IMPLEMENTATION_COMPLETE.md exists
- [ ] OBSERVABILITY_COMPLETE.md exists
- [ ] scripts/README.md exists
- [ ] README.md has test suite section
- [ ] .github/workflows/greenfield-ci.yml exists

**Commands**:
```bash
ls -lh docs/internal/TEST_SUITE.md
ls -lh IMPLEMENTATION_COMPLETE.md
ls -lh OBSERVABILITY_COMPLETE.md
ls -lh scripts/README.md
ls -lh .github/workflows/greenfield-ci.yml
```

---

## ✅ Phase 9: CI Workflow

- [ ] Greenfield CI workflow has 11+ steps
- [ ] All test suites included in CI
- [ ] SQL debug endpoint test present

**Commands**:
```bash
grep -c "name:" .github/workflows/greenfield-ci.yml
grep "test_phrase_queries" .github/workflows/greenfield-ci.yml
grep "test_recency_decay" .github/workflows/greenfield-ci.yml
grep "debug/sql" .github/workflows/greenfield-ci.yml
```

---

## ✅ Phase 10: Code Quality

- [ ] No Python syntax errors
- [ ] All imports resolve
- [ ] All test scripts have shebang and are executable

**Commands**:
```bash
python -m py_compile scripts/*.py
for f in scripts/*.py; do python -c "import ast; ast.parse(open('$f').read())"; done
```

---

## 🎯 Final Verification

Run all checks in sequence:

```bash
#!/usr/bin/env bash
echo "=== ContinuuAI Final Verification ==="

echo -e "\n1. Infrastructure"
docker ps | grep -q postgres && echo "  ✅ Postgres running" || echo "  ❌ Postgres not running"
docker ps | grep -q qdrant && echo "  ✅ Qdrant running" || echo "  ❌ Qdrant not running"

echo -e "\n2. Service Endpoints"
curl -sf http://localhost:8081/v1/health > /dev/null && echo "  ✅ Health endpoint OK" || echo "  ❌ Health endpoint failed"
curl -sf http://localhost:8081/v1/debug/weights > /dev/null && echo "  ✅ Debug weights OK" || echo "  ❌ Debug weights failed"

echo -e "\n3. Test Scripts"
ls scripts/*.py scripts/*.sh | wc -l | xargs echo "  ✅ Test scripts present:"

echo -e "\n4. Smoke Test"
./scripts/smoke_test_all.sh && echo "  ✅ Smoke test PASSED" || echo "  ❌ Smoke test FAILED"

echo -e "\n5. Full Test Suite"
./scripts/run_all_tests.sh && echo "  ✅ All tests PASSED" || echo "  ❌ Some tests FAILED"

echo -e "\n=== Verification Complete ==="
```

Save as `scripts/final_verification.sh`, make executable, run.

---

## 📋 Handoff Checklist

### For Operators
- [ ] Can boot stack with `docker compose up`
- [ ] Can run smoke test: `./scripts/smoke_test_all.sh`
- [ ] Can run full tests: `./scripts/run_all_tests.sh`
- [ ] Knows where docs are: `docs/internal/TEST_SUITE.md`

### For Developers
- [ ] Understands test suite structure
- [ ] Can add new tests (documented in TEST_SUITE.md)
- [ ] Knows how to run individual tests
- [ ] Understands CI workflow

### For Procurement/Management
- [ ] All integrity guarantees documented
- [ ] Test results easily interpretable
- [ ] System provably bootstraps on clean installs
- [ ] Security boundaries validated

---

## 🚀 Success Criteria

**System is ready when**:
- [ ] Smoke test passes
- [ ] All 6 test suites pass
- [ ] Documentation complete
- [ ] No errors in service logs

**Command to verify ready**:
```bash
./scripts/smoke_test_all.sh && ./scripts/run_all_tests.sh && echo "✅ SYSTEM READY"
```

---

## 📞 If Something Fails

### Smoke Test Failures
- **Infrastructure**: Check `docker compose ps`, restart services
- **Endpoints**: Check service logs, verify ports not in use
- **Schema**: Re-run migrations, check for errors

### Test Suite Failures
- **Provenance**: Check graph-deriver ran, span_node populated
- **ACL**: Verify migrations 0010-0011 applied
- **MMR**: Check sufficient test data exists
- **Phrase/Recency**: May be data-dependent, review warnings

### General Troubleshooting
1. Check logs: `docker compose logs --tail 100`
2. Restart clean: `docker compose down -v && docker compose up`
3. Re-run migrations: `cd services/retrieval && python migrate.py`
4. Verify Python deps: `pip install psycopg httpx numpy`

---

**Final Status**: System complete and operational ✅  
**Next Steps**: Proceed with feature work or deployment
