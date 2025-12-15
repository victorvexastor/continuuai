# PR: Add Greenfield Reproducibility CI and Provenance Invariants

## Summary
Adds proof-of-integrity layer for ContinuuAI: greenfield CI workflow and provenance invariant enforcement.

## What's Changed

### 1. `.github/workflows/greenfield-ci.yml`
Complete greenfield bootstrap CI that:
- Boots fresh Postgres 16 + Qdrant from scratch
- Applies all migrations in strict topological order
- Verifies migration hash integrity (drift detection)
- Starts retrieval service with full config
- Inserts synthetic evidence and runs graph-deriver
- Exercises `/v1/health` and `/v1/debug/weights` endpoints
- Runs retrieval synthetic test
- Validates provenance invariants

### 2. `scripts/check_invariants.py`
Executable contract that:
- Fetches retrieval results for a test query
- Validates every returned span has graph provenance via `span_node` or `edge_evidence`
- Fails CI (exit 2) if any span lacks accountability chain
- Proves "continuity, not vibes" claim

### 3. Migration Integrity
- Hash verification (SHA256) in CI prevents silent drift
- Detects when applied migrations diverge from source files
- Catches dev-prod schema mismatches before deployment

## Why This Matters

### For Engineering
- **Reproducibility**: "Works on clean install" is now provable, not aspirational
- **Integrity**: Continuity claims become executable contracts
- **Safety**: Catches hallucinated provenance before it reaches users
- **Drift Prevention**: Schema consistency enforced across all environments

### For Procurement/Buyers
- Transparent proof that system maintains accountability on fresh deploys
- Demonstrates operational maturity (not just "works on my laptop")
- Reduces DR/migration risk (provably bootstraps correctly)
- Audit-friendly: every result has traceable provenance

### For Future-You
- The immune system for the repo
- Prevents slow rot ("works on long-lived dev DB, explodes in prod")
- Makes onboarding new devs/environments deterministic
- Enables confident refactoring with invariant guardrails

## Testing
```bash
# Local verification (requires Docker)
docker compose up -d postgres qdrant
cd services/retrieval && python migrate.py
# CI workflow exercises full stack automatically
```

## Next Steps
After merge:
1. Add ACL negative tests (principal without scope → 0 results)
2. Add MMR property tests (diversity, deduplication)
3. Consider `/v1/debug/rules` endpoint for SQL observability (with auth gating)

## Checklist
- [x] Greenfield CI workflow complete and tested
- [x] Provenance invariants enforced in CI
- [x] Migration hash verification active
- [x] Scripts executable and documented
- [x] No breaking changes to existing services
- [x] Procurement-safe language in commit messages

---

**This PR adds zero runtime overhead** and zero production dependencies. It's pure verification infrastructure. The only reason not to merge it is if you *prefer* not knowing whether the system works on clean installs.
