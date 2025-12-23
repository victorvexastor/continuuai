# ContinuuAI Operations Guide

Internal reference for developers, DevOps, and system administrators.

## Quick Reference

**Services:**

| Service | Container | Port | Purpose |
|---------|-----------|------|--------|
| API Gateway | `continuuai-api-1` | 8080 | External API |
| Retrieval | `continuuai-retrieval-1` | 8081 | Evidence retrieval |
| Inference | `continuuai-inference-1` | 8082 | Response generation |
| Embedding | `continuuai-embedding-1` | 8083 | Vector embeddings |
| Graph Deriver | `continuuai-graph-deriver-1` | None | Background worker |
| PostgreSQL | `continuuai-postgres-1` | 5433 | Database |
| User App | `continuuai-user-app-1` | 3000 | Frontend |
| Admin Dashboard | `continuuai-admin-dashboard-1` | 3001 | Admin UI |

**Key Commands:**
```bash
# Start everything
make deploy
# or: docker compose up --build -d

# Watch logs
make logs
# or: docker compose logs -f

# Restart a service
docker compose restart retrieval

# Check health
curl http://localhost:8080/healthz

# Run test suite
make test
# or: ./scripts/run_all_tests.sh

# Database shell
make shell-db
# or: docker compose exec postgres psql -U continuuai -d continuuai
```

> **See also:** [Docker Container Access Guide](../how-to/DOCKER_CONTAINER_ACCESS.md) for detailed container interaction.

---

## Architecture

### Service Topology

```
External
  │
  ├─ API Gateway (:8080)
  │     ├─ POST /v1/query → Retrieval + Inference
  │     └─ POST /v1/ingest → Event Log
  │
Internal
  ├─ Retrieval Service (:8081)
  │     └─ Queries evidence_span with ACL filtering
  │
  ├─ Inference Service (:8082)
  │     └─ Validates JSON Schema, returns contract
  │
  ├─ Graph Deriver (background)
  │     └─ Polls event_log, builds graph_node/graph_edge
  │
  └─ PostgreSQL (:5433)
        └─ Single DB: cai_db
```

### Database Schema

**Core Tables:**
- `org` - Organizations
- `principal` - Users/services
- `role` - Role definitions
- `acl` - Access control lists
- `acl_allow` - ACL rules (principal→role→resource)

**Content Tables:**
- `artifact` - Documents/decisions (metadata)
- `artifact_text` - Full text content
- `evidence_span` - Extracted quotes with confidence scores

**Event System:**
- `event_log` - Append-only event log (idempotency_key for deduplication)
- `graph_node` - Derived knowledge graph nodes (decision/topic/artifact)
- `graph_edge` - Relationships (evidenced_by/supports/contradicts/relates)

### Design Principles

1. **Evidence-First**: Every response anchored in `evidence_span` with char positions
2. **Contract Enforcement**: JSON Schema validation at boundaries (inference + gateway)
3. **ACL in SQL**: Access control in database queries, not application logic
4. **Event Sourcing**: All writes to `event_log`, graph derived asynchronously
5. **Fail-Fast**: Validation errors return 500, not silent corruption

---

## Development Setup

### Prerequisites

- Docker 24+
- Docker Compose 2.20+
- curl/httpie (for testing)
- (Optional) psql client

### Initial Setup

```bash
# Clone repo
git clone <repo_url>
cd ContinuuAI

# Start stack (includes migrations + seed)
docker compose up --build -d

# Verify services
docker compose ps

# Run tests
./test_api.sh

# Check database
docker exec -it continuuai-postgres-1 psql -U cai cai_db -c '\dt'
```

### Local Development Workflow

```bash
# Edit code in services/*/
vim services/retrieval/main.py

# Rebuild only changed service
docker compose up --build -d retrieval

# Watch logs
docker compose logs -f retrieval

# Quick verify
curl http://localhost:8081/healthz
```

### Database Migrations

**Current**: Migrations run on container start via `migration-runner` service.

**Add New Migration:**

1. Create `migrations/0003_your_change.sql`
2. Ensure filename is lexicographically after previous (e.g., `0003` > `0002`)
3. Include idempotency (e.g., `CREATE TABLE IF NOT EXISTS`)
4. Rebuild: `docker compose up --build -d migrate`

**Manual Migration:**

```bash
docker exec -i continuuai-postgres-1 psql -U cai cai_db < migrations/0003_your_change.sql
```

### Seed Data

Default seed creates:
- Demo org: `00000000-0000-0000-0000-000000000000`
- Principal: `demo-user`
- ACLs: `public`, `engineering_team`, `exec_team`
- 3 sample evidence spans with confidence 0.78-0.92

**Reset Database:**

```bash
docker compose down -v  # WARNING: destroys all data
docker compose up --build -d
```

---

## Monitoring

### Health Checks

```bash
# Gateway health
curl http://localhost:8080/healthz

# Individual services
curl http://localhost:8081/healthz  # Retrieval
curl http://localhost:8082/healthz  # Inference
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f graph-deriver
docker compose logs -f retrieval

# Last 100 lines
docker compose logs --tail=100

# Search logs
docker compose logs | grep ERROR
```

> **See also:** [Logging & Observability Guide](LOGGING.md) for comprehensive log access and analysis.

### Database Queries

**Active connections:**
```sql
SELECT datname, usename, count(*) 
FROM pg_stat_activity 
GROUP BY datname, usename;
```

**Recent events:**
```sql
SELECT event_id, event_type, occurred_at, processed_at 
FROM event_log 
ORDER BY occurred_at DESC 
LIMIT 10;
```

**Evidence count by ACL:**
```sql
SELECT a.acl_name, count(es.evidence_span_id) 
FROM evidence_span es
JOIN artifact art ON es.artifact_id = art.artifact_id
JOIN acl a ON art.acl_id = a.acl_id
GROUP BY a.acl_name;
```

**Graph statistics:**
```sql
SELECT node_type, count(*) FROM graph_node GROUP BY node_type;
SELECT edge_type, count(*) FROM graph_edge GROUP BY edge_type;
```

### Performance Metrics

**Query response time:**
```bash
time curl -X POST http://localhost:8080/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"org_id":"00000000-0000-0000-0000-000000000000","principal_id":"user","mode":"recall","query_text":"test","scopes":[]}'
```

**Database query performance:**
```sql
SELECT query, calls, total_exec_time, mean_exec_time 
FROM pg_stat_statements 
ORDER BY total_exec_time DESC 
LIMIT 10;
```
(Requires `pg_stat_statements` extension)

---

## Troubleshooting

### Services Won't Start

```bash
# Check ports
lsof -i :8080  # API Gateway
lsof -i :5433  # PostgreSQL

# Check logs
docker compose logs

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Database Connection Errors

**Symptom:** `psycopg.OperationalError: connection refused`

**Fix:**
```bash
# Check postgres is running
docker compose ps postgres

# Check postgres logs
docker compose logs postgres

# Wait for postgres to be ready
docker compose up -d postgres
sleep 5
docker compose up -d
```

### Contract Validation Failures

**Symptom:** `500 Internal Server Error: Contract validation failed`

**Root Cause:** Inference service returned invalid JSON schema.

**Debug:**
1. Check inference service logs: `docker compose logs inference`
2. Manually test inference:
   ```bash
   curl http://localhost:8082/infer \
     -H 'Content-Type: application/json' \
     -d '{"mode":"recall","query_text":"test","evidence":[]}'
   ```
3. Validate response against `schemas/response-contract.v1.json`

### Graph Not Building

**Symptom:** No rows in `graph_node` or `graph_edge`

**Check:**
1. Events exist: `SELECT count(*) FROM event_log;`
2. Graph deriver is running: `docker compose ps graph-deriver`
3. Check logs: `docker compose logs graph-deriver`
4. Force reprocess:
   ```sql
   UPDATE event_log SET processed_at = NULL;
   ```
   Graph deriver will pick them up on next poll.

### Slow Queries

**Investigate:**
```sql
-- Current queries
SELECT pid, query, state, wait_event_type, now() - query_start AS runtime
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY runtime DESC;

-- Kill slow query
SELECT pg_terminate_backend(<pid>);
```

**Add indexes:**
```sql
-- Example: speed up evidence retrieval
CREATE INDEX CONCURRENTLY idx_evidence_span_created 
ON evidence_span(created_at DESC);
```

---

## Security

### Secrets Management

**Current**: Hardcoded in `docker-compose.yml`

**Production**: Use Docker secrets or external vault

```yaml
# docker-compose.yml (production)
secrets:
  db_password:
    external: true

services:
  postgres:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
```

### Network Isolation

**Current**: All services on same bridge network

**Production**: Separate networks

```yaml
networks:
  external:
    # API Gateway only
  internal:
    # Retrieval, Inference, Graph Deriver
  db:
    # PostgreSQL only
```

### TLS/SSL

**Current**: HTTP only (local dev)

**Production**: 
- API Gateway: Terminate TLS at load balancer
- Internal: mTLS between services
- Database: `require` SSL connections

---

## Deployment

### Local (Docker Compose)

```bash
docker compose up -d
```

### Staging/Production (Kubernetes)

**Helm Charts** (in `helm/` directory):

```bash
# Install
helm install continuuai helm/continuuai \
  --set image.tag=v0.1.0 \
  --set postgresql.password=<secret>

# Upgrade
helm upgrade continuuai helm/continuuai

# Check status
kubectl get pods -l app=continuuai
```

**Manual kubectl:**

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl rollout status deployment/api-gateway

# View logs
kubectl logs -l app=api-gateway --tail=100
```

### Environment Variables

**API Gateway:**
- `RETRIEVAL_URL` (default: `http://retrieval:8081`)
- `INFERENCE_URL` (default: `http://inference:8082`)
- `LOG_LEVEL` (default: `INFO`)

**Retrieval/Inference:**
- `DATABASE_URL` (default: `postgres://cai:cai@postgres:5432/cai_db`)
- `LOG_LEVEL` (default: `INFO`)

**Graph Deriver:**
- `DATABASE_URL` (same as above)
- `POLL_INTERVAL_SEC` (default: `10`)

---

## Backup & Restore

### Database Backup

```bash
# Full backup
docker exec continuuai-postgres-1 pg_dump -U cai cai_db | gzip > backup-$(date +%F).sql.gz

# Restore
gunzip -c backup-2025-01-15.sql.gz | docker exec -i continuuai-postgres-1 psql -U cai cai_db
```

### Incremental Backup (WAL archiving)

See `docs/internal/TECHNICAL_DESIGN.md` for PostgreSQL WAL archiving setup.

---

## Performance Tuning

### Database

**Connection pooling:**
```python
# In services/*/main.py
import psycopg_pool
pool = psycopg_pool.ConnectionPool(dsn, min_size=2, max_size=10)
```

**Indexes:**
```sql
-- Evidence retrieval
CREATE INDEX idx_evidence_span_acl ON evidence_span(artifact_id);
CREATE INDEX idx_artifact_org ON artifact(org_id);

-- Graph queries
CREATE INDEX idx_graph_edge_from ON graph_edge(from_node_id);
CREATE INDEX idx_graph_edge_to ON graph_edge(to_node_id);
```

**Vacuum:**
```sql
-- Check bloat
SELECT schemaname, relname, n_dead_tup FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;

-- Run vacuum
VACUUM ANALYZE;
```

### API Services

**Concurrency:**
```bash
# Increase uvicorn workers
docker compose up -d --scale api-gateway=3
```

**Caching:**
- Add Redis for frequent queries
- Cache evidence spans for 60s TTL

### Graph Deriver

**Batch processing:**
```python
# Process 100 events per poll instead of 10
cursor.execute("SELECT * FROM event_log WHERE processed_at IS NULL LIMIT 100")
```

---

## Testing

### Unit Tests

```bash
# (Future) Run pytest in services
docker compose run --rm retrieval pytest tests/
```

### Integration Tests

```bash
# Full test suite
./test_api.sh

# Expected output:
# ✅ Health check
# ✅ /v1/query (recall mode)
# ✅ /v1/ingest
# ✅ Graph nodes: 6 created
# ✅ Graph edges: 8 created
```

### Load Testing

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test /v1/query
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -D query.json \
  http://localhost:8080/v1/query

# Analyze results
# Target: p95 < 200ms, no errors
```

### Contract Validation Tests

```bash
# Validate response against schema
curl http://localhost:8080/v1/query \
  -H 'Content-Type: application/json' \
  -d '...' | \
  docker run --rm -i ghcr.io/ajv-validator/ajv-cli:latest \
    validate -s /schemas/response-contract.v1.json
```

---

## Data Management

### Purge Old Events

```sql
-- Archive events older than 90 days
BEGIN;
COPY (SELECT * FROM event_log WHERE occurred_at < now() - interval '90 days') 
TO '/tmp/archive.csv' CSV HEADER;
DELETE FROM event_log WHERE occurred_at < now() - interval '90 days';
COMMIT;
```

### Reset Demo Data

```bash
docker compose down -v
docker compose up --build -d
```

### Export Evidence

```sql
-- Export to CSV
COPY (
  SELECT es.evidence_span_id, a.acl_name, es.quote, es.confidence
  FROM evidence_span es
  JOIN artifact art ON es.artifact_id = art.artifact_id
  JOIN acl a ON art.acl_id = a.acl_id
) TO '/tmp/evidence.csv' CSV HEADER;
```

---

## Scaling Strategies

### Horizontal Scaling

**Services:**
- API Gateway: Scale to N replicas behind load balancer
- Retrieval/Inference: Scale independently based on load
- Graph Deriver: Single instance (use locks if multiple)

**Database:**
- Read replicas for query-heavy workloads
- Partition `event_log` by org_id for multi-tenant

### Vertical Scaling

**PostgreSQL:**
- Increase `shared_buffers` (25% of RAM)
- Increase `effective_cache_size` (50% of RAM)
- Tune `work_mem` based on query complexity

**API Services:**
- Increase uvicorn workers (`--workers 4`)
- Increase connection pool size

### Caching

**Query results:**
- Cache frequent queries in Redis (60s TTL)
- Invalidate on new ingests to same topic

**Evidence spans:**
- Precompute for common scopes
- Refresh every 5 minutes

---

## Maintenance Windows

### Recommended Schedule

- **Daily**: Log rotation, temp table cleanup
- **Weekly**: Database vacuum analyze
- **Monthly**: Review slow queries, update indexes
- **Quarterly**: Major version upgrades

### Zero-Downtime Deployment

```bash
# 1. Deploy new version alongside old
kubectl apply -f k8s/deployment-v2.yaml

# 2. Run smoke tests
./test_api.sh v2.example.com

# 3. Switch traffic (gradually)
kubectl set image deployment/api-gateway api-gateway=continuuai:v0.2.0

# 4. Monitor errors
kubectl logs -l app=api-gateway --tail=100

# 5. Rollback if needed
kubectl rollout undo deployment/api-gateway
```

---

## Compliance & Auditing

### Access Logs

```sql
-- Query audit log (future feature)
SELECT principal_id, query_text, accessed_acls, timestamp
FROM query_audit_log
WHERE timestamp > now() - interval '24 hours';
```

### Data Retention

```sql
-- Set retention policy
CREATE TABLE event_log_archive (LIKE event_log);
ALTER TABLE event_log_archive SET (autovacuum_enabled = false);

-- Archive quarterly
INSERT INTO event_log_archive 
SELECT * FROM event_log 
WHERE occurred_at < now() - interval '90 days';
```

### GDPR Compliance

**Right to erasure:**
```sql
-- Delete user's data
DELETE FROM event_log WHERE actor_external_subject = 'user@example.com';
DELETE FROM evidence_span WHERE artifact_id IN (
  SELECT artifact_id FROM artifact WHERE payload->>'owner' = 'user@example.com'
);
```

---

## Emergency Procedures

### Database Corruption

```bash
# 1. Stop all writes
docker compose stop api-gateway

# 2. Verify corruption
docker exec continuuai-postgres-1 psql -U cai cai_db -c "SELECT pg_check(datname) FROM pg_database WHERE datname='cai_db';"

# 3. Restore from backup
./scripts/restore_backup.sh backup-2025-01-15.sql.gz

# 4. Restart
docker compose up -d
```

### Service Outage

```bash
# Check status
docker compose ps

# Restart failed service
docker compose restart <service>

# View recent logs
docker compose logs --tail=50 <service>

# Escalate if needed
# Contact: ops@continuuai.org
```

### Runaway Process

```bash
# Identify
docker stats

# Kill container
docker stop <container_id>

# Investigate
docker logs <container_id>

# Prevent restart
docker compose down <service>
```

---

## Contact & Escalation

- **On-Call**: ops@continuuai.org
- **Security Issues**: security@continuuai.org
- **GitHub Issues**: https://github.com/continuuai/continuuai/issues
- **Internal Slack**: #continuuai-ops

---

## Changelog

### v0.1.0 (Current)
- Initial microservices architecture
- Docker Compose deployment
- Event sourcing + graph derivation
- ACL-based access control

### Roadmap
- v0.2.0: Kubernetes Helm charts, monitoring (Prometheus/Grafana)
- v0.3.0: Real LLM integration, semantic search
- v0.4.0: Multi-tenant, authentication, rate limiting
- v1.0.0: Production-ready, SOC2 compliance

---

## Additional Resources

### Quick Links
- [Docker Container Access](../how-to/DOCKER_CONTAINER_ACCESS.md) - Access and interact with containers
- [Logging & Observability](LOGGING.md) - Log access and analysis
- [Graph Deriver Reference](../reference/GRAPH_DERIVER.md) - Background daemon details

### Technical Documentation
- [Technical Design](../reference/TECHNICAL_DESIGN.md) - System architecture
- [SQL Schema Reference](../reference/sql-schema.md) - Database structure
- [API Reference](../reference/API_REFERENCE.md) - API documentation
- [Test Suite Reference](../reference/TEST_SUITE.md) - Testing documentation

### Conceptual Documentation
- [ContinuuAI Vision](../explanation/CONTINUUAI_VISION.md) - Philosophy and goals

### Deployment
- [Deployment Guide](../../DEPLOYMENT.md) - Installation and setup
- [.env.example](../../.env.example) - Configuration reference
