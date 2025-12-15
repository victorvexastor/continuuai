# ContinuuAI Test Suite & Integrity Guarantees

## Overview
The ContinuuAI system includes a comprehensive test suite that enforces continuity, security, and quality contracts. These tests run in CI and can be executed locally to verify system integrity.

---

## Test Categories

### 1. Greenfield Reproducibility (`greenfield-ci.yml`)
**Purpose**: Proves the system bootstraps correctly on fresh installs

**What it tests**:
- Fresh Postgres 16 + Qdrant deployment
- Migration topological ordering (pgvector before vector columns, etc.)
- Migration hash integrity (drift detection)
- Services start and respond correctly
- Health and debug endpoints operational

**Why it matters**:
- Prevents "works on dev, explodes in prod" scenarios
- Enables confident DR/migration procedures
- Makes onboarding deterministic

**Run locally**:
```bash
docker compose down -v  # Clean slate
docker compose up -d postgres qdrant
cd services/retrieval && python migrate.py
# Verify services boot correctly
```

---

### 2. Provenance Invariants (`check_invariants.py`)
**Purpose**: Enforces that every returned span has graph accountability

**What it tests**:
- Every retrieval result links to `span_node` OR `edge_evidence`
- No "hallucinated" spans without provenance chain
- Continuity claims are executable contracts, not aspirations

**Why it matters**:
- Core system promise: "continuity, not vibes"
- Audit-friendly: every result is traceable
- Catches data integrity bugs before users see them

**Contract**:
```python
# For every span in retrieval results:
assert (
    exists(span_node WHERE evidence_span_id = span.id) OR
    exists(edge_evidence WHERE evidence_span_id = span.id)
)
```

**Run locally**:
```bash
python scripts/check_invariants.py
# Exit 0: all spans have provenance
# Exit 2: invariant violated (includes failing span IDs)
```

---

### 3. ACL Negative Tests (`test_acl_negative.py`)
**Purpose**: Proves access control boundaries hold under adversarial conditions

**What it tests**:

#### Test 1: No Scope → Zero Results
- Principal with no role/scope gets **zero results**
- Even if matching content exists in the database
- Catches "filter after top-k" bugs

#### Test 2: Partial Scope → Filtered Results
- Principal with role granting access to subset of artifacts
- Results contain **only** permitted artifacts
- Blocked artifacts never leak through

#### Test 3: Policy Blocks All Seeds
- Seed vector/lexical matches exist but policy denies all
- Result set is **empty** (not filtered post-retrieval)
- Proves ACL enforcement happens **before** scoring/ranking

**Why it matters**:
- Security boundary validation (not just positive-path testing)
- Procurement requirement: multi-tenancy isolation
- Regulatory compliance (GDPR, SOC 2, etc.)

**Run locally**:
```bash
python scripts/test_acl_negative.py
# Creates test principals and artifacts with known boundaries
# Verifies zero-trust enforcement
```

---

### 4. MMR Property Tests (`test_mmr_properties.py`)
**Purpose**: Validates diversity and deduplication claims

**What it tests**:

#### Test 1: Diversity Increases
- MMR results have **lower average pairwise similarity** than greedy top-k
- Measured via Jaccard similarity on text tokens
- Proves diversity mechanism works

#### Test 2: Deduplication Reduces Overlaps
- MMR with dedup threshold reduces spans from **same artifact**
- Prevents "10 variants of same paragraph" result sets
- Improves user experience

#### Test 3: Quality Preserved
- Top result quality doesn't degrade **>25%** with MMR
- Balances diversity vs. relevance
- Ensures MMR doesn't sacrifice correctness for novelty

**Why it matters**:
- Quality assurance for core retrieval claims
- Prevents silent degradation over time
- Data-driven validation (not just "feels better")

**Run locally**:
```bash
python scripts/test_mmr_properties.py
# Compares greedy vs MMR retrieval on same query
# Reports diversity, deduplication, and quality metrics
```

---

### 5. Phrase Query Validation (`test_phrase_queries.py`) ✅ NEW
**Purpose**: Verifies quoted queries shift lexical weights correctly

**What it tests**:

#### Test 1: Phrase vs Bag-of-Words
- Phrase query `"exact match"` returns different results than bag-of-words
- Validates websearch_to_tsquery behavior

#### Test 2: Phrase Match Prioritization
- Exact phrase matches should rank higher than scattered word matches
- Validates lexical scoring correctness

#### Test 3: No Phrase Match Fallback
- Queries with no phrase match degrade gracefully
- Falls back to bag-of-words semantics

#### Test 4: Websearch Operators
- `AND`, `OR`, `-` operators work as expected
- Validates advanced search syntax

**Why it matters**:
- UI-friendly query building (users expect quotes to work)
- Precision search for exact phrases
- Validates Postgres full-text search integration

**Run locally**:
```bash
python scripts/test_phrase_queries.py
# Tests phrase queries vs bag-of-words
# Verifies websearch_to_tsquery operators
```

---

### 6. Recency Decay Validation (`test_recency_decay.py`) ✅ NEW
**Purpose**: Verifies halflife parameter produces expected decay curves

**What it tests**:

#### Test 1: Halflife Boundary
- Decay factor at halflife point is ~0.5
- Validates exponential decay formula: `POW(0.5, age_days / halflife)`

#### Test 2: Recent vs Old Scoring
- Recent spans (< halflife) score higher than old spans (> halflife)
- All else equal, recency influences ranking

#### Test 3: Monotonic Decay
- Decay function is monotonic (older = strictly lower or equal)
- No unexpected inversions

#### Test 4: Zero Weight Disables Decay
- When `DELTA_RECENCY=0`, decay doesn't influence scores
- Config validation

**Why it matters**:
- Temporal relevance (recent decisions matter more)
- Configurable via `RECENCY_HALFLIFE_DAYS`
- Prevents stale content dominating results

**Run locally**:
```bash
python scripts/test_recency_decay.py
# Tests decay math against DB
# Validates monotonicity and boundaries
```

---

### 7. SQL Debug Endpoint (`/v1/debug/sql`) ✅ NEW
**Purpose**: Exposes active SQL fragments for observability

**Security**: 
- Gated by `ADMIN_DEBUG_TOKEN` environment variable
- Only enabled in non-prod or with valid token
- Returns 403 Forbidden if token invalid/missing

**What it exposes**:
- Vector search query template
- Lexical (BM25) search with websearch_to_tsquery
- Graph expansion CTE
- ACL filter query
- Recency decay formula
- MMR deduplication

**Run locally**:
```bash
# Without token (dev mode)
curl http://localhost:8081/v1/debug/sql | jq .

# With token (prod mode)
curl "http://localhost:8081/v1/debug/sql?admin_token=SECRET" | jq .
```

**Why it matters**:
- Operational transparency
- Debugging query performance
- Understanding retrieval behavior
- Security: only admins see query structure

---

## Test Execution Matrix

| Test Suite | CI | Local | Exit on Fail | Requires Data |
|------------|----|----|--------------|---------------|
| Greenfield CI | ✅ | ✅ | Yes | No (synthetic) |
| Provenance Invariants | ✅ | ✅ | Yes | Yes |
| ACL Negative | ✅ | ✅ | Yes | No (creates fixtures) |
| MMR Properties | ✅ | ✅ | Yes | Yes |
| Phrase Query Validation | ✅ | ✅ | Yes | Yes |
| Recency Decay Validation | ✅ | ✅ | Yes | Yes |
| SQL Debug Endpoint | ✅ | ✅ | No (optional) | No |

---

## CI Workflow Summary

```yaml
# .github/workflows/greenfield-ci.yml
1. Boot Postgres 16 + Qdrant (fresh containers)
2. Apply migrations (strict order, hash verification)
3. Start retrieval service (full config)
4. Insert synthetic evidence
5. Run graph-deriver
6. Test /health and /debug/weights endpoints
7. Run retrieval synthetic test
8. ✅ Validate provenance invariants
9. ✅ Run ACL negative tests
10. ✅ Run MMR property tests
11. Summary: all contracts verified
```

---

## Integrity Guarantees

### What These Tests Prove

1. **Reproducibility**: System bootstraps correctly on clean installs
2. **Accountability**: Every result has traceable graph provenance
3. **Security**: Access control boundaries hold under adversarial conditions
4. **Quality**: MMR diversity/deduplication work as claimed
5. **Consistency**: Schema drift is detected before deployment

### What These Tests Prevent

- "Works on my laptop" syndrome
- Hallucinated/orphaned spans in production
- ACL bypass vulnerabilities
- Silent degradation of retrieval quality
- Dev-prod schema mismatches

---

## Adding New Tests

### Checklist
1. Create test script in `scripts/test_*.py`
2. Make executable: `chmod +x scripts/test_*.py`
3. Add to `.github/workflows/greenfield-ci.yml`
4. Document in this file
5. Verify exit codes (0=pass, non-zero=fail)

### Test Design Principles
- **Executable contracts**: tests encode system promises
- **Property-based**: test invariants, not specific values
- **Reproducible**: deterministic or clearly document variance
- **Fast**: <5s per test suite locally
- **Isolated**: tests don't depend on each other

---

## Maintenance

### When Migrations Change
- Greenfield CI will catch topological violations
- Hash verification will catch drift
- Re-run locally to verify: `python services/retrieval/migrate.py`

### When Retrieval Logic Changes
- MMR properties may need threshold adjustments
- Provenance invariants should never fail (hard contract)
- ACL tests should always pass (security boundary)

### When Adding New Node Types
- Update `GRAPH_BONUS_MAP` in `.env` and CI
- Add property tests if new diversity characteristics expected
- Verify provenance for new entity types

---

## Procurement/Buyer View

**Q: How do we know the system works on a clean install?**  
A: Greenfield CI boots fresh infrastructure and validates end-to-end

**Q: How do we know results are trustworthy?**  
A: Provenance invariants fail CI if any span lacks accountability

**Q: How do we know access control works?**  
A: ACL negative tests prove zero-trust enforcement under adversarial conditions

**Q: How do we know quality won't degrade?**  
A: MMR property tests lock diversity/deduplication contracts

**Q: What happens if schema drifts between environments?**  
A: Migration hash verification detects and blocks deployment

---

## Next Steps

### Potential Future Tests
1. **Phrase Query Validation**: quoted queries shift lexical weights correctly
2. **Recency Decay Boundaries**: halflife parameter produces expected curves
3. **SQL Observability**: `/v1/debug/rules` endpoint (gated) exposes active queries
4. **Load Testing**: k6 scripts for sustained throughput/latency
5. **Chaos Testing**: kill services mid-query, verify graceful degradation

### Integration Opportunities
- Pre-commit hooks for local test runs
- Slack/email notifications on CI failures
- Datadog/Prometheus metrics from test runs
- Snapshot testing for ranking stability (with clear versioning)

---

**Last Updated**: 2025-12-15  
**Status**: All test suites operational and integrated into CI
