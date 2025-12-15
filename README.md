# ContinuuAI

**Evidence-First Organizational Memory & Decision Intelligence**

A privacy-respecting, evidence-anchored AI system that tracks decisions, maintains continuity, and ensures every answer traces to verifiable sources.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM available
- Ports 8080-8082 and 5432 available

### Run Locally

```bash
# Start all services
docker compose up --build

# Wait for services to start (about 2-3 minutes)
# You'll see "migrations complete" and "seed complete" in the logs
```

### Test the System

#### 1. Query for Recall (retrieve existing decisions)

```bash
curl -s http://localhost:8080/v1/query \
  -H 'content-type: application/json' \
  -d '{
    "org_id":"00000000-0000-0000-0000-000000000000",
    "principal_id":"p1",
    "mode":"recall",
    "query_text":"What did we decide about Feature X?",
    "scopes":["team:eng"]
  }' | jq
```

#### 2. Ingest a New Decision

```bash
curl -s http://localhost:8080/v1/ingest \
  -H 'content-type: application/json' \
  -d '{
    "org_id":"00000000-0000-0000-0000-000000000000",
    "actor_external_subject":"p1",
    "event_type":"decision.recorded",
    "idempotency_key":"demo-2",
    "payload":{
      "topic":"infrastructure",
      "decision_key":"decision:k8s_migration",
      "decision_title":"Migrate to Kubernetes"
    },
    "text_utf8":"Decision: Migrate services to Kubernetes. Rationale: better scaling and resilience. Timeline: Q1 2025. Risk: team learning curve."
  }' | jq
```

#### 3. Inspect the Decision Graph

```bash
# View graph nodes
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai \
  -c "SELECT node_type, key, title FROM graph_node ORDER BY created_at DESC LIMIT 10;"

# View graph edges
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai \
  -c "SELECT e.edge_type, n1.key as src, n2.key as dst FROM graph_edge e 
      JOIN graph_node n1 ON n1.node_id=e.src_node_id 
      JOIN graph_node n2 ON n2.node_id=e.dst_node_id 
      ORDER BY e.created_at DESC LIMIT 10;"
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     API Gateway (:8080)                      │
│  • /v1/query (retrieval + inference orchestration)          │
│  • /v1/ingest (write events + evidence spans)               │
└────────────────┬──────────────────────┬────────────────────┘
                 │                       │
       ┌─────────▼─────────┐   ┌────────▼─────────┐
       │  Retrieval (:8081)│   │ Inference (:8082)│
       │  • Query evidence │   │ • Validate schema│
       │  • ACL filtering  │   │ • Anchor to proof│
       └─────────┬─────────┘   └──────────────────┘
                 │
       ┌─────────▼──────────────────────────────────┐
       │         PostgreSQL (:5432)             │
       │  • org, principal, role, acl           │
       │  • artifact, artifact_text             │
       │  • evidence_span (quotes + confidence) │
       │  • event_log (append-only)             │
       │  • graph_node, graph_edge              │
       └─────────▲──────────────────────────┬──┘
                 │                            │
       ┌─────────┴─────────┐        ┌────────▼─────────┐
       │  Migrate (startup)│        │  Graph Deriver   │
       │  • Apply SQL      │        │  • Process events│
       └───────────────────┘        │  • Build graph   │
       ┌───────────────────┐        └──────────────────┘
       │   Seed (startup)  │
       │  • Demo org + data│
       └───────────────────┘
```

## Key Concepts

### Evidence Spans

Every answer is anchored to specific text spans with:
- `start_char` / `end_char` - exact position in source text
- `confidence` - 0.0 to 1.0 score
- `section_path` - hierarchical location
- `extracted_by` - provenance tracking

### Response Contract

All responses validate against `schemas/response-contract.v1.json`:
- `contract_version` - schema version
- `mode` - recall | reflection | projection
- `answer` - natural language response
- `evidence[]` - array of evidence spans with quotes
- `policy` - status (ok | insufficient_evidence | policy_denied)
- `debug` - arbitrary metadata

### ACL Model

Policy-first access control:
- Every `artifact` has an `acl_id`
- ACLs grant access to `principal` (user) or `role`
- Retrieval **never** returns evidence the user can't access

### Event Sourcing

All changes flow through `event_log`:
- Append-only (immutable history)
- Idempotency keys prevent duplicates
- `processed_at` tracks graph derivation

## Development

### Project Structure

```
ContinuuAI/
├── migrations/          # SQL schema files
├── schemas/             # JSON Schema validation contracts
├── services/
│   ├── api-gateway/    # FastAPI orchestrator
│   ├── retrieval/      # Evidence query service
│   ├── inference/      # Contract-validated stub
│   ├── graph-deriver/  # Async graph builder
│   ├── migrate/        # Migration runner
│   └── seed/           # Demo data loader
├── docker-compose.yml  # Local development stack
├── README.md           # This file
├── TECHNICAL_DESIGN.md # Detailed architecture
└── CONTINUUAI_VISION.md # Vision, promise, roadmap
```

## Monitoring

### Health Checks

```bash
curl http://localhost:8080/healthz
```

### Logs

```bash
docker compose logs -f api
docker compose logs -f retrieval
docker compose logs -f graph-deriver
```

## Troubleshooting

### Services won't start

```bash
# Restart clean
docker compose down -v
docker compose up --build
```

### Migrations fail

```bash
# Connect to Postgres
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai

# Check migration status
SELECT * FROM schema_migrations;
```

## Documentation

### For Users

- **[Getting Started Guide](docs/external/GETTING_STARTED.md)** - Quick setup and first queries
- **[API Reference](docs/external/API_REFERENCE.md)** - Complete endpoint documentation
- **[Vision & Philosophy](docs/external/CONTINUUAI_VISION.md)** - Why ContinuuAI exists
- **[External Docs Index](docs/external/README.md)** - Full user documentation

### For Developers

- **[Operations Guide](docs/internal/OPERATIONS.md)** - Day-to-day operations and troubleshooting
- **[Technical Design](docs/internal/TECHNICAL_DESIGN.md)** - Architecture and system design
- **[Local Development](docs/internal/LOCAL.md)** - Local setup workflow
- **[SQL Schema](docs/internal/sql-schema.md)** - Database reference
- **[Internal Docs Index](docs/internal/README.md)** - Full technical documentation

## What Makes This Different

- **Evidence-First**: Every answer traces to verifiable sources
- **Contract-Validated**: Strict schemas at every boundary
- **Policy-Respectful**: ACLs enforced in data layer
- **Privacy-Conscious**: PII classification + retention policies
- **Community-Funded**: Profits support NGO mission

See [CONTINUUAI_VISION.md](CONTINUUAI_VISION.md) for the full story.
