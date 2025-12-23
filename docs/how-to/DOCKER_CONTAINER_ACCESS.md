# Docker Container Access Guide

How to access, monitor, and interact with ContinuuAI's Docker containers.

---

## Quick Reference

| Service | Container Name | Port | Access Method |
|---------|---------------|------|---------------|
| PostgreSQL | `continuuai-postgres-1` | 5433 | `docker compose exec postgres psql` |
| API Gateway | `continuuai-api-1` | 8080 | `curl http://localhost:8080` |
| Retrieval | `continuuai-retrieval-1` | 8081 | `curl http://localhost:8081` |
| Inference | `continuuai-inference-1` | 8082 | `curl http://localhost:8082` |
| Embedding | `continuuai-embedding-1` | 8083 | `curl http://localhost:8083` |
| Graph Deriver | `continuuai-graph-deriver-1` | None | Logs only |
| Admin Dashboard | `continuuai-admin-dashboard-1` | 3001 | `http://localhost:3001` |
| User App | `continuuai-user-app-1` | 3000 | `http://localhost:3000` |

---

## Viewing Container Status

### List All Containers

```bash
# Show running containers
docker compose ps

# Show all containers (including stopped)
docker compose ps -a

# Detailed status with health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Check Resource Usage

```bash
# Live resource stats
docker stats

# One-time snapshot
docker stats --no-stream

# Using Makefile
make top
```

---

## Accessing Container Logs

### Real-Time Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f postgres
docker compose logs -f graph-deriver
docker compose logs -f retrieval
docker compose logs -f inference
docker compose logs -f embedding
```

### Historical Logs

```bash
# Last 100 lines
docker compose logs --tail=100 api

# Last 500 lines with timestamps
docker compose logs --tail=500 -t graph-deriver

# Logs since specific time
docker compose logs --since 1h api
docker compose logs --since "2025-12-15T10:00:00" graph-deriver
```

### Filtering Logs

```bash
# Search for errors
docker compose logs api | grep -i error

# Search for specific patterns
docker compose logs graph-deriver | grep "Processing"
docker compose logs retrieval | grep "ACL"

# Filter by log level
docker compose logs api | grep -E "(ERROR|WARNING)"
```

### Using Makefile Shortcuts

```bash
make logs           # All services
make logs-api       # API Gateway
make logs-db        # PostgreSQL
make logs-retrieval # Retrieval service
make logs-inference # Inference service
make logs-graph     # Graph Deriver
```

---

## Shell Access to Containers

### Getting a Shell

```bash
# PostgreSQL container (has bash)
docker compose exec postgres bash

# Python service containers (use sh or python)
docker compose exec api /bin/sh
docker compose exec retrieval /bin/sh
docker compose exec graph-deriver /bin/sh

# Node.js containers (Next.js apps)
docker compose exec admin-dashboard /bin/sh
docker compose exec user-app /bin/sh
```

### Running Commands Inside Containers

```bash
# Run a single command
docker compose exec postgres psql -U continuuai -d continuuai -c "SELECT 1;"

# Run Python script
docker compose exec api python -c "print('hello')"

# Check installed packages
docker compose exec api pip list
docker compose exec retrieval pip list
```

---

## Database Access

### PostgreSQL Shell

```bash
# Using docker compose
docker compose exec postgres psql -U continuuai -d continuuai

# Using Makefile
make shell-db

# Direct connection from host (if port exposed)
psql -h localhost -p 5433 -U continuuai -d continuuai
```

### Useful Database Commands

```sql
-- List tables
\dt

-- Describe table
\d graph_node

-- Count records
SELECT count(*) FROM event_log;
SELECT count(*) FROM graph_node;
SELECT count(*) FROM evidence_span;

-- Recent events
SELECT event_id, event_type, occurred_at 
FROM event_log 
ORDER BY occurred_at DESC 
LIMIT 10;

-- Graph statistics
SELECT node_type, count(*) FROM graph_node GROUP BY node_type;
SELECT edge_type, count(*) FROM graph_edge GROUP BY edge_type;

-- Active connections
SELECT datname, usename, count(*) FROM pg_stat_activity GROUP BY datname, usename;
```

### Database Backup & Restore

```bash
# Backup
make backup
# Creates: backups/backup-YYYYMMDD-HHMMSS.sql

# Manual backup
docker compose exec postgres pg_dump -U continuuai continuuai > backup.sql

# Restore
make restore BACKUP=backups/backup-20251215-120000.sql

# Manual restore
docker compose exec -T postgres psql -U continuuai continuuai < backup.sql
```

---

## API Service Access

### Health Checks

```bash
# Gateway health
curl http://localhost:8080/healthz

# Retrieval health
curl http://localhost:8081/v1/health

# Inference health
curl http://localhost:8082/healthz

# Embedding health
curl http://localhost:8083/v1/health
```

### Debug Endpoints

```bash
# Retrieval debug info (requires debug token)
curl -H "X-Debug-Token: debug_token" http://localhost:8081/v1/debug/weights
curl -H "X-Debug-Token: debug_token" http://localhost:8081/v1/debug/sql
```

### Test Query

```bash
# Query the API
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "principal_id": "p1",
    "mode": "recall",
    "query_text": "What decisions have we made?",
    "scopes": []
  }'
```

### Ingest Data

```bash
curl -X POST http://localhost:8080/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "event_type": "decision.recorded",
    "text_utf8": "We decided to use PostgreSQL for the database.",
    "payload": {
      "kind": "decision",
      "title": "Database Selection"
    }
  }'
```

---

## Graph Deriver Access

The Graph Deriver has no exposed ports—it's a background worker. Access it through logs and database queries.

### View Processing

```bash
# Watch logs
docker compose logs -f graph-deriver

# Filter for processing events
docker compose logs graph-deriver | grep "Processing"
docker compose logs graph-deriver | grep "Deriving"
```

### Check Processing State

```sql
-- In PostgreSQL shell
-- Check derivation progress
SELECT org_id, last_event_id, last_processed_at 
FROM graph_derivation_state;

-- Check unprocessed events
SELECT count(*) FROM event_log 
WHERE processed_at IS NULL;

-- Recent graph nodes created
SELECT node_type, key, title, created_at 
FROM graph_node 
ORDER BY created_at DESC 
LIMIT 10;
```

### Force Reprocessing

```sql
-- Reset derivation state (will reprocess all events)
DELETE FROM graph_derivation_state;
```

Then restart the deriver:
```bash
docker compose restart graph-deriver
```

---

## Container Management

### Starting/Stopping

```bash
# Start all
docker compose up -d
make deploy

# Stop all
docker compose stop
make stop

# Restart all
docker compose restart
make restart

# Restart specific service
docker compose restart graph-deriver
docker compose restart api
```

### Rebuilding

```bash
# Rebuild all images
docker compose build
make build

# Rebuild specific service
docker compose build graph-deriver

# Rebuild and restart
docker compose up --build -d graph-deriver
```

### Cleanup

```bash
# Stop and remove containers (keep volumes)
docker compose down
make clean

# Stop and remove containers AND volumes (destructive!)
docker compose down -v

# Full reset
make reset
```

---

## Copying Files To/From Containers

### Copy Files Out

```bash
# Copy file from container to host
docker compose cp api:/app/app.py ./app.py

# Copy directory
docker compose cp postgres:/var/lib/postgresql/data ./pg-data-backup
```

### Copy Files In

```bash
# Copy file into container
docker compose cp ./my-script.py api:/tmp/my-script.py

# Execute copied script
docker compose exec api python /tmp/my-script.py
```

---

## Inspecting Containers

### View Container Details

```bash
# Full container info
docker inspect continuuai-api-1

# Just environment variables
docker inspect continuuai-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}'

# Just network settings
docker inspect continuuai-api-1 --format '{{json .NetworkSettings.Networks}}'

# Image info
docker inspect continuuai-api-1 --format '{{.Config.Image}}'
```

### View Mounted Volumes

```bash
docker inspect continuuai-postgres-1 --format '{{json .Mounts}}'
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for startup errors
docker compose logs api | head -50

# Check if port is in use
lsof -i :8080

# Rebuild from scratch
docker compose down
docker compose build --no-cache api
docker compose up -d api
```

### Container Keeps Restarting

```bash
# Check restart count
docker inspect continuuai-api-1 --format '{{.RestartCount}}'

# View exit code
docker inspect continuuai-api-1 --format '{{.State.ExitCode}}'

# View OOM killer
docker inspect continuuai-api-1 --format '{{.State.OOMKilled}}'

# Increase memory if OOM
# Add to docker-compose.yml under service:
# deploy:
#   resources:
#     limits:
#       memory: 512M
```

### Network Issues

```bash
# List networks
docker network ls

# Inspect network
docker network inspect continuuai_default

# Check container can reach another
docker compose exec api ping postgres
```

### Database Connection Issues

```bash
# Test connection from API container
docker compose exec api python -c "import psycopg; psycopg.connect('postgres://continuuai:continuuai@postgres:5432/continuuai').execute('SELECT 1').fetchone()"

# Check PostgreSQL is accepting connections
docker compose exec postgres pg_isready -U continuuai
```

---

## Useful Aliases

Add these to your `.bashrc` or `.zshrc`:

```bash
# ContinuuAI shortcuts
alias cai-logs='docker compose -f /path/to/ContinuuAI/docker-compose.yml logs -f'
alias cai-ps='docker compose -f /path/to/ContinuuAI/docker-compose.yml ps'
alias cai-db='docker compose -f /path/to/ContinuuAI/docker-compose.yml exec postgres psql -U continuuai -d continuuai'
alias cai-restart='docker compose -f /path/to/ContinuuAI/docker-compose.yml restart'

# Quick status check
cai-status() {
    echo "=== Containers ===" 
    docker compose -f /path/to/ContinuuAI/docker-compose.yml ps
    echo ""
    echo "=== Health Checks ==="
    curl -s http://localhost:8080/healthz | jq .
    echo ""
    echo "=== Graph Stats ==="
    docker compose -f /path/to/ContinuuAI/docker-compose.yml exec -T postgres psql -U continuuai -d continuuai -c "SELECT node_type, count(*) FROM graph_node GROUP BY node_type;"
}
```

---

## See Also

- [Graph Deriver Reference](../reference/GRAPH_DERIVER.md) - Detailed deriver documentation
- [Operations Guide](../operations/OPERATIONS.md) - Day-to-day operations
- [Deployment Guide](../../DEPLOYMENT.md) - Initial setup
- [Troubleshooting](../operations/OPERATIONS.md#troubleshooting) - Common issues
