# ContinuuAI Logging & Observability

How logging works across ContinuuAI services, and how to access and analyze logs.

---

## Overview

ContinuuAI uses structured logging across all services. Each service outputs logs to stdout/stderr, which Docker captures and makes available via `docker compose logs`.

**Logging Stack:**
- **Python services**: Python `logging` module (Graph Deriver, Retrieval, API Gateway)
- **FastAPI services**: uvicorn access logs + application logs
- **Next.js apps**: Console logging
- **PostgreSQL**: PostgreSQL native logging

---

## Log Levels

| Level | When Used |
|-------|-----------|
| `DEBUG` | Detailed debugging (disabled in production) |
| `INFO` | Normal operation, key events, request processing |
| `WARNING` | Recoverable issues, deprecation notices |
| `ERROR` | Failures, exceptions, action required |
| `CRITICAL` | System failure, immediate action required |

Set via environment variable:
```bash
LOG_LEVEL=INFO  # Default
LOG_LEVEL=DEBUG # Development
```

---

## Service-Specific Logging

### Graph Deriver

**Location**: `services/graph-deriver/app.py`

**Configuration**:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("graph-deriver")
```

**Log Format**:
```
2025-12-15 10:00:00,123 INFO graph-deriver Starting graph-deriver, polling every 10s
2025-12-15 10:00:10,456 INFO graph-deriver Processing 3 new events for org 00000000-...
2025-12-15 10:00:10,789 INFO graph-deriver Deriving from event abc123, kind=decision
2025-12-15 10:00:10,999 ERROR graph-deriver Failed to derive from event xyz789: ...
```

**Key Log Patterns**:
```bash
# Watch event processing
docker compose logs -f graph-deriver | grep "Processing"

# Watch derivation activity
docker compose logs -f graph-deriver | grep "Deriving"

# Watch errors only
docker compose logs -f graph-deriver | grep "ERROR"
```

### API Gateway

**Location**: `services/api-gateway/app.py`

**Logging**: FastAPI/uvicorn default + custom logs

**Log Format**:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     192.168.1.1:50000 - "POST /v1/query HTTP/1.1" 200 OK
INFO:     192.168.1.1:50001 - "POST /v1/ingest HTTP/1.1" 200 OK
```

**Key Log Patterns**:
```bash
# Watch all API requests
docker compose logs -f api

# Filter by endpoint
docker compose logs api | grep "/v1/query"
docker compose logs api | grep "/v1/ingest"

# Filter by status code
docker compose logs api | grep "500"
docker compose logs api | grep "400"
```

### Retrieval Service

**Location**: `services/retrieval/app.py`

**Logging**: FastAPI/uvicorn + custom retrieval metrics

**Key Log Patterns**:
```bash
# Watch retrieval requests
docker compose logs -f retrieval

# Watch evidence retrieval
docker compose logs retrieval | grep "evidence"

# Watch ACL filtering
docker compose logs retrieval | grep "ACL"
```

### Inference Service

**Location**: `services/inference/app.py`

**Logging**: FastAPI/uvicorn + inference timing

**Key Log Patterns**:
```bash
# Watch inference requests
docker compose logs -f inference

# Watch response generation
docker compose logs inference | grep "response"
```

### PostgreSQL

**Native PostgreSQL logging** (in container):

```bash
# View PostgreSQL logs
docker compose logs postgres

# Watch connections
docker compose logs postgres | grep "connection"

# Watch queries (if enabled)
docker compose logs postgres | grep "statement:"
```

**Enable Query Logging** (for debugging):
```sql
-- In PostgreSQL shell
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
```

---

## Viewing Logs

### Real-Time Monitoring

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f graph-deriver
docker compose logs -f api
docker compose logs -f postgres

# Multiple services
docker compose logs -f api retrieval inference
```

### Historical Logs

```bash
# Last N lines
docker compose logs --tail=100 api
docker compose logs --tail=500 graph-deriver

# With timestamps
docker compose logs -t api

# Since specific time
docker compose logs --since 1h api
docker compose logs --since "2025-12-15T10:00:00" graph-deriver

# Until specific time
docker compose logs --until "2025-12-15T11:00:00" api
```

### Filtering & Searching

```bash
# Search for errors
docker compose logs api | grep -i error

# Search for warnings
docker compose logs | grep -i warning

# Search by log level
docker compose logs | grep -E "(ERROR|WARNING)"

# Case-insensitive pattern
docker compose logs | grep -i "connection"

# Show context around matches
docker compose logs | grep -B2 -A2 "ERROR"

# Count occurrences
docker compose logs | grep -c "ERROR"
```

### Saving Logs

```bash
# Save to file
docker compose logs > logs.txt

# Save specific service
docker compose logs api > api-logs.txt

# Save with compression
docker compose logs | gzip > logs-$(date +%F).txt.gz
```

---

## Makefile Shortcuts

```bash
make logs           # All services (real-time)
make logs-api       # API Gateway
make logs-db        # PostgreSQL
make logs-retrieval # Retrieval service
make logs-inference # Inference service
make logs-graph     # Graph Deriver
```

---

## Structured Log Patterns

### Request/Response Logging

API Gateway logs include:
- Client IP
- HTTP method and path
- Response status code
- Response time (uvicorn)

### Event Processing

Graph Deriver logs include:
- Organization ID
- Event count per batch
- Event ID and type being processed
- Node/edge creation results

### Error Logging

All services log errors with:
- Exception type
- Error message
- Stack trace (when appropriate)

---

## Log Rotation

Docker handles log rotation automatically. Configure in `docker-compose.yml`:

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Or in Docker daemon config (`/etc/docker/daemon.json`):
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  }
}
```

---

## Debug Mode

Enable verbose logging for development:

```bash
# In .env
LOG_LEVEL=DEBUG
DEV_MODE=true

# Restart services
docker compose restart
```

Debug endpoints (when DEV_MODE=true):
```bash
# Retrieval debug info
curl -H "X-Debug-Token: debug_token" http://localhost:8081/v1/debug/weights
curl -H "X-Debug-Token: debug_token" http://localhost:8081/v1/debug/sql
```

---

## Common Log Analysis

### Count Events by Type

```bash
docker compose logs graph-deriver | grep "Deriving" | awk '{print $NF}' | sort | uniq -c
```

### Track Error Rate

```bash
# Errors per minute
docker compose logs --since 1h api | grep "ERROR" | cut -d' ' -f1 | uniq -c
```

### Find Slow Requests

```bash
# Requests taking > 1s (uvicorn logs response time)
docker compose logs api | grep -E "took [1-9][0-9]*\.[0-9]+s"
```

### Check Processing Backlog

```bash
# Graph deriver processing stats
docker compose logs graph-deriver | grep "Processing" | tail -20
```

---

## Integration with External Systems

### Shipping to Loki/Grafana

Add loki driver to docker-compose:
```yaml
services:
  api:
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-batch-size: "100"
```

### Shipping to CloudWatch

```yaml
services:
  api:
    logging:
      driver: awslogs
      options:
        awslogs-region: us-east-1
        awslogs-group: continuuai
        awslogs-stream: api
```

### Shipping to ELK Stack

Use Filebeat or Fluentd as a sidecar, or configure Logstash to read from Docker socket.

---

## Troubleshooting via Logs

### Service Won't Start

```bash
# Check startup logs
docker compose logs api | head -50

# Look for import errors
docker compose logs api | grep -i "import"

# Look for connection errors
docker compose logs api | grep -i "connect"
```

### 500 Errors

```bash
# Find the error
docker compose logs api | grep -B5 "500"

# Get full traceback
docker compose logs api | grep -A20 "Traceback"
```

### Graph Not Building

```bash
# Check deriver is processing
docker compose logs graph-deriver | grep "Processing"

# Check for extraction errors
docker compose logs graph-deriver | grep "ERROR"

# Check database connectivity
docker compose logs graph-deriver | grep "connect"
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose logs postgres | grep -i error

# Check connection attempts
docker compose logs postgres | grep "connection"

# Check from service side
docker compose logs api | grep "postgres"
```

---

## Best Practices

1. **Use structured logging**: Include context (org_id, event_id, user_id) in log messages
2. **Log at appropriate levels**: INFO for normal ops, ERROR for failures
3. **Don't log secrets**: Redact passwords, tokens, PII
4. **Include correlation IDs**: trace_id for request tracing
5. **Log entry and exit**: For important functions, log start and completion
6. **Configure rotation**: Prevent disk exhaustion from logs

---

## See Also

- [Docker Container Access](../how-to/DOCKER_CONTAINER_ACCESS.md) - Container interaction
- [Operations Guide](OPERATIONS.md) - Day-to-day operations
- [Graph Deriver Reference](../reference/GRAPH_DERIVER.md) - Deriver details
- [Troubleshooting](OPERATIONS.md#troubleshooting) - Common issues
