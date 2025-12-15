# ContinuuAI Internal Documentation

Technical documentation for developers, DevOps, and system administrators.

## Quick Links

### Operations
- **[Operations Guide](OPERATIONS.md)** - Day-to-day operations, monitoring, troubleshooting
- **[Technical Design](TECHNICAL_DESIGN.md)** - Architecture decisions, system design
- **[Local Development](LOCAL.md)** - Local setup and development workflow

### Reference
- **[SQL Schema](sql-schema.md)** - Complete database schema reference
- **[Configuration](cp.md)** - Configuration and deployment details
- **[Status](STATUS.md)** - Current implementation status and roadmap

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway (:8080)                   │
│                                                              │
│  POST /v1/query  → Retrieval + Inference                    │
│  POST /v1/ingest → Event Log                                │
└──────────────────┬───────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│  Retrieval   │      │  Inference   │
│   Service    │      │   Service    │
│   (:8081)    │      │   (:8082)    │
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  ▼
          ┌──────────────┐
          │  PostgreSQL  │
          │    (:5433)   │
          └──────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │ Graph Deriver  │
        │  (background)  │
        └────────────────┘
```

### Services

| Service | Port | Purpose | Public |
|---------|------|---------|--------|
| API Gateway | 8080 | External API, orchestration | ✅ |
| Retrieval | 8081 | Evidence span queries + ACL filtering | ❌ |
| Inference | 8082 | Contract validation + response synthesis | ❌ |
| PostgreSQL | 5433 | Single source of truth | ❌ |
| Graph Deriver | - | Async graph builder | ❌ |

### Database Tables

**Core (Identity & Access)**
- `org` - Organizations
- `principal` - Users/services
- `role` - Role definitions  
- `acl` - Access control lists
- `acl_allow` - ACL rules

**Content**
- `artifact` - Document metadata
- `artifact_text` - Full text
- `evidence_span` - Extracted quotes with confidence

**Events & Graph**
- `event_log` - Append-only event log
- `graph_node` - Knowledge graph nodes
- `graph_edge` - Relationships

## Development Workflow

### Quick Start

```bash
# 1. Clone and start
git clone <repo>
cd ContinuuAI
docker compose up --build -d

# 2. Verify
./test_api.sh

# 3. Check logs
docker compose logs -f api-gateway
```

### Make a Change

```bash
# Edit code
vim services/retrieval/main.py

# Rebuild only changed service
docker compose up --build -d retrieval

# Test
curl http://localhost:8081/healthz
```

### Add Database Migration

```bash
# 1. Create migration file
cat > migrations/0003_add_index.sql <<EOF
CREATE INDEX CONCURRENTLY idx_evidence_span_created 
ON evidence_span(created_at DESC);
EOF

# 2. Apply
docker compose up --build -d migrate

# 3. Verify
docker exec -it continuuai-postgres-1 psql -U cai cai_db -c '\di'
```

## Key Design Decisions

### 1. Evidence-First Architecture

**Decision**: Every response MUST include `evidence_span` quotes with char positions

**Rationale**: 
- Prevents LLM hallucinations
- Enables verification
- Supports compliance/audit

**Implementation**:
- `evidence_span` table with `start_char`, `end_char`, `confidence`
- JSON Schema validation enforces `evidence[]` array
- Retrieval service filters by ACL at query time

### 2. Contract Enforcement

**Decision**: JSON Schema validation at inference service + gateway boundaries

**Rationale**:
- Fail-fast: catch schema violations before returning to user
- Type safety across service boundaries
- Self-documenting API contract

**Implementation**:
- `schemas/response-contract.v1.json` (Draft 2020-12)
- Inference service validates before returning
- Gateway validates before forwarding to user

### 3. ACL in SQL

**Decision**: Access control in database queries, not application logic

**Rationale**:
- Single source of truth
- Impossible to forget ACL check
- Database-level audit trail

**Implementation**:
```sql
-- Retrieval service query
SELECT es.* FROM evidence_span es
JOIN artifact art ON es.artifact_id = art.artifact_id
JOIN acl a ON art.acl_id = a.acl_id
JOIN acl_allow aa ON a.acl_id = aa.acl_id
WHERE aa.principal_id = $1  -- ACL filter here
```

### 4. Event Sourcing

**Decision**: All writes to `event_log`, graph derived asynchronously

**Rationale**:
- Complete audit trail
- Replay events for graph rebuild
- Idempotency via `idempotency_key`

**Implementation**:
- API Gateway writes to `event_log` on `/v1/ingest`
- Graph Deriver polls `WHERE processed_at IS NULL`
- Updates `processed_at` after processing

## Common Tasks

### Debugging Slow Query

```bash
# 1. Check logs
docker compose logs retrieval | grep "slow query"

# 2. Enable slow query log in postgres
docker exec -it continuuai-postgres-1 psql -U cai cai_db
ALTER DATABASE cai_db SET log_min_duration_statement = 100;

# 3. View slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;

# 4. Add index
CREATE INDEX CONCURRENTLY idx_fix ON table(column);
```

### Resetting Database

```bash
# WARNING: Destroys all data
docker compose down -v
docker compose up --build -d
```

### Testing Contract Validation

```bash
# Manually test inference service
curl http://localhost:8082/infer \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "recall",
    "query_text": "test",
    "evidence": [
      {
        "evidence_span_id": "test",
        "artifact_id": "test",
        "quote": "test quote",
        "confidence": 0.9
      }
    ]
  }'

# Should return contract-valid JSON
```

### Viewing Graph

```sql
-- Graph statistics
SELECT node_type, count(*) FROM graph_node GROUP BY node_type;
SELECT edge_type, count(*) FROM graph_edge GROUP BY edge_type;

-- Specific decision's connections
SELECT gn.*, ge.edge_type
FROM graph_node gn
JOIN graph_edge ge ON gn.node_id = ge.to_node_id
WHERE ge.from_node_id = 'decision-uuid';
```

## Monitoring Checklist

Daily:
- [ ] All services healthy: `docker compose ps`
- [ ] No error logs: `docker compose logs | grep ERROR`
- [ ] Graph deriver processing: `SELECT count(*) FROM event_log WHERE processed_at IS NULL`

Weekly:
- [ ] Database vacuum: `VACUUM ANALYZE;`
- [ ] Review slow queries
- [ ] Test suite passes: `./test_api.sh`

Monthly:
- [ ] Review indexes
- [ ] Update dependencies
- [ ] Review security alerts

## Known Limitations (v0.1.0)

**By Design (for Phase 1)**:
- ❌ No semantic search (keyword + recent only)
- ❌ Stub inference (no real LLM)
- ❌ No authentication (demo org hardcoded)
- ❌ No rate limiting
- ❌ Single-tenant (org_id hardcoded)

**Future Roadmap**:
- v0.2.0: Authentication, webhooks, pagination
- v0.3.0: Semantic search (embeddings + hybrid scoring)
- v0.4.0: Real LLM integration (OpenAI, Anthropic, local)
- v1.0.0: Multi-tenant, SOC2, production-ready

## Security Notes

### Current State (Dev)
- Hardcoded credentials in `docker-compose.yml`
- No TLS (HTTP only)
- No authentication
- Single network (no isolation)

### Production Requirements
- [ ] Secrets in external vault (HashiCorp Vault, AWS Secrets Manager)
- [ ] TLS termination at load balancer
- [ ] mTLS between services
- [ ] Network isolation (separate db/internal/external networks)
- [ ] Authentication (JWT tokens)
- [ ] Rate limiting (Redis + sliding window)
- [ ] Audit logging (structured logs to SIEM)

## Performance Targets

### v0.1.0 (Current)
- Cold start: < 5s (migrations + seed)
- Query response: < 500ms p95
- Ingest: < 200ms p95
- Graph derivation: < 10s lag

### v1.0.0 (Production)
- Query response: < 150ms p95 (with caching)
- Ingest: < 100ms p95
- Graph derivation: < 1s lag
- Concurrent users: 1000+ per instance
- Database size: 100GB+ (with partitioning)

## Testing Strategy

### Unit Tests (Future)
```bash
docker compose run --rm retrieval pytest tests/unit/
```

### Integration Tests (Current)
```bash
./test_api.sh
```

### Load Tests
```bash
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -D query.json \
  http://localhost:8080/v1/query
```

### Contract Tests
```bash
# Validate response against schema
curl http://localhost:8080/v1/query ... | \
  docker run --rm -i ghcr.io/ajv-validator/ajv-cli:latest \
    validate -s /schemas/response-contract.v1.json
```

## Deployment Checklist

### Staging
- [ ] Build images: `docker compose build`
- [ ] Tag images: `docker tag continuuai-api-gateway:latest continuuai-api-gateway:v0.1.0`
- [ ] Push to registry: `docker push continuuai-api-gateway:v0.1.0`
- [ ] Update Helm values: `image.tag=v0.1.0`
- [ ] Deploy: `helm upgrade continuuai helm/continuuai`
- [ ] Run smoke tests: `./test_api.sh staging.example.com`
- [ ] Monitor logs: `kubectl logs -l app=api-gateway --tail=100`

### Production
- [ ] All staging checks passed
- [ ] Security scan: `trivy image continuuai-api-gateway:v0.1.0`
- [ ] Backup database: `pg_dump ...`
- [ ] Update image tag in Helm
- [ ] Deploy with canary: `helm upgrade --set replicaCount=2`
- [ ] Watch error rate: `kubectl top pods`
- [ ] Rollback if needed: `helm rollback continuuai`

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Services won't start | Port conflict | `lsof -i :8080`, change port |
| Database connection error | Postgres not ready | `docker compose up -d postgres && sleep 5` |
| Contract validation failed | Invalid inference response | Check `docker compose logs inference` |
| Graph not building | Graph deriver not running | `docker compose ps graph-deriver` |
| Slow queries | Missing index | `CREATE INDEX CONCURRENTLY ...` |
| 502 Bad Gateway | Upstream service down | `docker compose ps`, `docker compose restart <service>` |

## Contact

- **Internal Slack**: #continuuai-dev
- **On-Call**: ops@continuuai.org
- **Security**: security@continuuai.org
- **GitHub**: https://github.com/continuuai/continuuai

---

**For user-facing docs, see**: [`docs/external/`](../external/README.md)
