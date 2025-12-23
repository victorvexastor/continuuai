# Graph Deriver Service

**Service Type**: Background Daemon (Worker)  
**Container Name**: `continuuai-graph-deriver-1`  
**Port**: None (no exposed ports)  
**Source**: `services/graph-deriver/app.py`

---

## Overview

The Graph Deriver is a background worker that continuously polls the `event_log` table and extracts structured graph nodes and edges from ingested events. It builds ContinuuAI's knowledge graph—the semantic network of decisions, assumptions, outcomes, risks, and relationships.

**Key Responsibilities:**
- Poll for new events in `event_log`
- Extract entities (decisions, assumptions, outcomes, risks, people, priorities)
- Create graph nodes and edges with evidence links
- Maintain derivation state per organization

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Log                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ event_id │ event_type │ payload │ processed_at │ ...     │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ polls every POLL_INTERVAL_SEC
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Graph Deriver                              │
│  ┌────────────────────┐    ┌─────────────────────────────────┐ │
│  │ Event Processing   │───▶│ Node/Edge Extraction            │ │
│  │ (per org)          │    │ • Decision nodes                │ │
│  │                    │    │ • Assumption nodes              │ │
│  │                    │    │ • Outcome nodes                 │ │
│  │                    │    │ • Risk nodes                    │ │
│  │                    │    │ • Person/Priority nodes         │ │
│  └────────────────────┘    └────────────────┬────────────────┘ │
└──────────────────────────────────────────────┼──────────────────┘
                                               │ writes to
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐ │
│  │ graph_node    │  │ graph_edge    │  │ edge_evidence       │ │
│  │               │◀─│               │◀─│                     │ │
│  └───────────────┘  └───────────────┘  └─────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────┐                       │
│  │ graph_derivation_state              │                       │
│  │ (tracks last_event_id per org)      │                       │
│  └─────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `postgres` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `continuuai` | Database name |
| `DB_USER` | `continuuai` | Database user |
| `DB_PASS` | `dev_password` | Database password |
| `POLL_INTERVAL_SEC` | `10` | Seconds between polling cycles |

### Docker Compose Configuration

```yaml
graph-deriver:
  build:
    context: .
    dockerfile: services/graph-deriver/Dockerfile
  environment:
    DB_HOST: postgres
    DB_PORT: "5432"
    DB_NAME: ${POSTGRES_DB:-continuuai}
    DB_USER: ${POSTGRES_USER:-continuuai}
    DB_PASS: ${POSTGRES_PASSWORD:-continuuai}
    POLL_INTERVAL_SEC: ${POLL_INTERVAL_SEC:-10}
  restart: ${RESTART_POLICY:-unless-stopped}
  depends_on:
    postgres:
      condition: service_healthy
    migrate:
      condition: service_completed_successfully
    seed:
      condition: service_completed_successfully
```

---

## How It Works

### 1. Main Daemon Loop

The service runs an infinite loop:

```python
while True:
    # Connect to PostgreSQL
    conn = psycopg2.connect(...)
    
    # Get all organizations
    orgs = get_all_org_ids()
    
    # Process events for each org
    for org_id in orgs:
        last_event_id = get_derivation_state(org_id)
        new_events = fetch_events_after(last_event_id)
        
        for event in new_events:
            derive_from_event(event)
            update_derivation_state(org_id, event.event_id)
    
    # Sleep before next poll
    time.sleep(POLL_INTERVAL_SEC)
```

### 2. Entity Extraction Rules

The deriver extracts different entity types based on the `payload.kind` field:

#### Decision Events (`kind: "decision"`)
Creates:
- **Decision node**: The main decision with title, description, priority
- **Person node**: Owner if specified
- **Assumption nodes**: For each assumption in the payload
- **Priority node**: Links decision to priority level

Edges:
- `decision --decided_by--> person`
- `decision --depends_on--> assumption`
- `decision --relates_to--> priority`

#### Outcome Events (`kind: "outcome"`)
Creates:
- **Outcome node**: Result with title and description

Edges:
- `decision --affects--> outcome` (if `decision_ref` provided)

#### Risk Events (`kind: "risk"`)
Creates:
- **Risk node**: With severity metadata

Edges:
- `risk --affects--> target_node` (if `relates_to` provided)

#### Generic Events (other types)
Creates:
- **Event node**: Generic event record

### 3. Stable Node Keys

Nodes are deduplicated using stable hashing:

```python
def stable_hash(org_id: str, text: str) -> str:
    """Generate stable node key from org + text"""
    return hashlib.sha256(f"{org_id}:{text}".encode()).hexdigest()[:24]
```

This ensures:
- Same decision text → same node key → upsert (not duplicate)
- Different orgs → different keys (org isolation)

### 4. Evidence Linking

Every edge is linked back to source evidence:

```python
def attach_edge_evidence(edge_id, event_id):
    """Link edge to evidence spans from source event"""
    # 1. Find evidence_spans for the event's artifact
    # 2. Insert edge_evidence records
    # 3. Populate span_node table (if exists)
```

This maintains the evidence trail:
`edge → edge_evidence → evidence_span → artifact_text → artifact`

---

## Accessing the Service

### View Logs

```bash
# Real-time logs
docker compose logs -f graph-deriver

# Recent logs
docker compose logs --tail=100 graph-deriver

# Filter for specific patterns
docker compose logs graph-deriver | grep "Processing"
docker compose logs graph-deriver | grep "ERROR"
```

### Shell Access

```bash
# Get a shell inside the container
docker compose exec graph-deriver /bin/bash

# Or with sh (if bash not available)
docker compose exec graph-deriver /bin/sh
```

### Check Service Status

```bash
# Container status
docker compose ps graph-deriver

# Resource usage
docker stats continuuai-graph-deriver-1
```

### Restart Service

```bash
# Restart the deriver
docker compose restart graph-deriver

# Force rebuild and restart
docker compose up --build -d graph-deriver
```

---

## Monitoring

### Logging Output

The service logs structured messages at INFO level:

```
2025-12-15 10:00:00,123 INFO graph-deriver Starting graph-deriver, polling every 10s
2025-12-15 10:00:10,456 INFO graph-deriver Processing 3 new events for org 00000000-0000-0000-0000-000000000000
2025-12-15 10:00:10,789 INFO graph-deriver Deriving from event abc123, kind=decision
```

### Database Queries

Check derivation state:
```sql
SELECT org_id, last_event_id, last_processed_at 
FROM graph_derivation_state;
```

Check graph statistics:
```sql
-- Node counts by type
SELECT node_type, count(*) 
FROM graph_node 
GROUP BY node_type 
ORDER BY count(*) DESC;

-- Edge counts by type
SELECT edge_type, count(*) 
FROM graph_edge 
GROUP BY edge_type 
ORDER BY count(*) DESC;

-- Recent nodes
SELECT node_type, key, title, created_at 
FROM graph_node 
ORDER BY created_at DESC 
LIMIT 10;
```

Check unprocessed events:
```sql
SELECT count(*) FROM event_log WHERE processed_at IS NULL;
```

---

## Troubleshooting

### Graph Not Building

**Symptoms:** No rows in `graph_node` or `graph_edge`

**Debug Steps:**

1. Check if events exist:
   ```sql
   SELECT count(*) FROM event_log;
   ```

2. Check deriver is running:
   ```bash
   docker compose ps graph-deriver
   ```

3. Check logs for errors:
   ```bash
   docker compose logs --tail=50 graph-deriver | grep -i error
   ```

4. Force reprocess all events:
   ```sql
   -- Reset derivation state
   DELETE FROM graph_derivation_state;
   ```
   Then restart the deriver.

### Duplicate Nodes

**Cause:** Likely a bug in stable_hash or key generation

**Debug:**
```sql
SELECT org_id, node_type, key, count(*) 
FROM graph_node 
GROUP BY org_id, node_type, key 
HAVING count(*) > 1;
```

### Connection Errors

**Symptom:** `psycopg2.OperationalError: connection refused`

**Fix:**
1. Ensure PostgreSQL is running: `docker compose ps postgres`
2. Check DB credentials match `.env`
3. Restart: `docker compose restart graph-deriver`

### High Memory Usage

**Cause:** Processing too many events at once

**Tune:**
- Reduce `POLL_INTERVAL_SEC` to process more frequently in smaller batches
- Check for event backlog: `SELECT count(*) FROM event_log WHERE processed_at IS NULL;`

---

## Development

### Local Testing

```bash
# Run deriver locally (requires DB connection)
cd services/graph-deriver
DATABASE_URL="postgres://continuuai:continuuai@localhost:5433/continuuai" \
  python app.py
```

### Adding New Entity Types

1. Add extraction logic in `derive_from_event()`:
   ```python
   elif kind == "new_entity_type":
       title = payload.get("title", "Default")
       # Create node
       node_id = self.upsert_node(...)
       # Create edges
       edge_id = self.upsert_edge(...)
       # Link evidence
       self.attach_edge_evidence(edge_id, event_id)
   ```

2. Define node_type and edge_type constants

3. Test with sample event:
   ```bash
   curl -X POST http://localhost:8080/v1/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "org_id": "00000000-0000-0000-0000-000000000000",
       "event_type": "test.new_entity",
       "text_utf8": "Test content",
       "payload": {"kind": "new_entity_type", "title": "Test"}
     }'
   ```

### File Structure

```
services/graph-deriver/
├── Dockerfile       # Python 3.11-slim, psycopg2-binary
├── app.py          # Main daemon and GraphDeriver class (active)
└── deriver.py      # Alternative implementation (unused)
```

---

## Database Schema Reference

### graph_node
```sql
CREATE TABLE graph_node (
    node_id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    node_type VARCHAR(50) NOT NULL,   -- decision, assumption, outcome, risk, person, priority, event
    key VARCHAR(255) NOT NULL,        -- stable hash
    title TEXT NOT NULL,
    canonical_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (org_id, node_type, key)
);
```

### graph_edge
```sql
CREATE TABLE graph_edge (
    edge_id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    src_node_id UUID REFERENCES graph_node,
    dst_node_id UUID REFERENCES graph_node,
    edge_type VARCHAR(50) NOT NULL,   -- decided_by, depends_on, relates_to, affects
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (org_id, src_node_id, dst_node_id, edge_type)
);
```

### edge_evidence
```sql
CREATE TABLE edge_evidence (
    edge_id UUID REFERENCES graph_edge,
    evidence_span_id UUID REFERENCES evidence_span,
    confidence FLOAT,
    evidence_type VARCHAR(50),        -- derived_from_event, keyword_match, decision_ref
    created_by VARCHAR(100),
    PRIMARY KEY (edge_id, evidence_span_id)
);
```

### graph_derivation_state
```sql
CREATE TABLE graph_derivation_state (
    org_id UUID PRIMARY KEY,
    last_event_id UUID,
    last_processed_at TIMESTAMP
);
```

---

## See Also

- [Technical Design](TECHNICAL_DESIGN.md) - System architecture
- [SQL Schema Reference](sql-schema.md) - Full database schema
- [Operations Guide](../operations/OPERATIONS.md) - Day-to-day operations
- [API Reference](API_REFERENCE.md) - Ingestion endpoints
