Yep. Here’s the **next concrete slice**: add `/v1/ingest` to the gateway, persist an **event_log row + artifact + artifact_text + evidence_spans**, then run a **graph-deriver** that turns events into a simple **decision graph**.

Below is copy/paste code for:

* **New migrations** (DB schema)
* **Gateway `/v1/ingest`** (writes event_log + evidence spans)
* **Graph deriver service** (polls event_log, updates graph tables)
* **Docker compose additions** (so it runs end-to-end)

---

## 1) Migrations

Create these files in `migrations/` (in order).

### `migrations/0001_init.sql`

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Org + identity
CREATE TABLE IF NOT EXISTS org (
  org_id uuid PRIMARY KEY,
  org_slug text NOT NULL UNIQUE,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS principal (
  principal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  principal_type text NOT NULL CHECK (principal_type IN ('user','service','group')),
  external_subject text NOT NULL,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, external_subject)
);

CREATE TABLE IF NOT EXISTS role (
  role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  role_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, role_name)
);

-- ACLs
CREATE TABLE IF NOT EXISTS acl (
  acl_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, name)
);

CREATE TABLE IF NOT EXISTS acl_allow (
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  acl_id uuid NOT NULL REFERENCES acl(acl_id) ON DELETE CASCADE,
  allow_type text NOT NULL CHECK (allow_type IN ('principal','role')),
  principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE CASCADE,
  role_id uuid NULL REFERENCES role(role_id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (acl_id, allow_type, principal_id, role_id),
  CHECK (
    (allow_type='principal' AND principal_id IS NOT NULL AND role_id IS NULL) OR
    (allow_type='role' AND role_id IS NOT NULL AND principal_id IS NULL)
  )
);

-- Artifacts + text
CREATE TABLE IF NOT EXISTS artifact (
  artifact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  source_system text NOT NULL,
  source_uri text NOT NULL,
  source_etag text NULL,

  captured_at timestamptz NOT NULL DEFAULT now(),
  occurred_at timestamptz NOT NULL DEFAULT now(),

  author_principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE SET NULL,

  content_type text NOT NULL,
  storage_uri text NOT NULL,
  sha256 bytea NOT NULL,
  size_bytes bigint NOT NULL DEFAULT 0,

  acl_id uuid NOT NULL REFERENCES acl(acl_id) ON DELETE RESTRICT,
  pii_classification text NOT NULL DEFAULT 'none',

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_org_time ON artifact(org_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS artifact_text (
  artifact_text_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  artifact_id uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,

  normaliser_version text NOT NULL,
  language text NOT NULL DEFAULT 'en',
  text_utf8 text NOT NULL,
  text_sha256 bytea NOT NULL,
  structure_json jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_text_org_art ON artifact_text(org_id, artifact_id);

-- Evidence spans
CREATE TABLE IF NOT EXISTS evidence_span (
  evidence_span_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  artifact_id uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,
  artifact_text_id uuid NOT NULL REFERENCES artifact_text(artifact_text_id) ON DELETE CASCADE,

  span_type text NOT NULL DEFAULT 'text',
  start_char int NOT NULL,
  end_char int NOT NULL,
  section_path text NOT NULL DEFAULT '',
  extracted_by text NOT NULL,
  confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),

  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (end_char >= start_char)
);

CREATE INDEX IF NOT EXISTS idx_evidence_org_created ON evidence_span(org_id, created_at DESC);
```

### `migrations/0002_event_log_and_graph.sql`

```sql
-- Append-only event log (source of truth)
CREATE TABLE IF NOT EXISTS event_log (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  event_type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  ingested_at timestamptz NOT NULL DEFAULT now(),

  actor_principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE SET NULL,

  -- pointers to artifacts created by ingest (optional)
  artifact_id uuid NULL REFERENCES artifact(artifact_id) ON DELETE SET NULL,

  -- typed payload (later: enforce via protobuf / JSON schema)
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- idempotency + trace
  idempotency_key text NULL,
  trace_id text NULL,

  -- processing cursor
  processed_at timestamptz NULL,

  UNIQUE(org_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_event_org_time ON event_log(org_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_unprocessed ON event_log(org_id, processed_at) WHERE processed_at IS NULL;

-- Minimal decision graph
CREATE TABLE IF NOT EXISTS graph_node (
  node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  node_type text NOT NULL CHECK (node_type IN ('decision','topic','artifact')),
  key text NOT NULL,          -- stable-ish identifier (e.g. "decision:feature_x_flag")
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, node_type, key)
);

CREATE TABLE IF NOT EXISTS graph_edge (
  edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  src_node_id uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  dst_node_id uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  edge_type text NOT NULL CHECK (edge_type IN ('supports','contradicts','relates','evidenced_by')),
  weight double precision NOT NULL DEFAULT 1.0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, src_node_id, dst_node_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_edge_org_src ON graph_edge(org_id, src_node_id);
CREATE INDEX IF NOT EXISTS idx_edge_org_dst ON graph_edge(org_id, dst_node_id);
```

---

## 2) Add `/v1/ingest` to the gateway

Replace your `services/api-gateway/app.py` with the version below (it keeps `/v1/query` and adds ingest).

### `services/api-gateway/app.py`

```python
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator, validate
from pydantic import BaseModel, Field

app = FastAPI(title="Continuuai API Gateway", version="0.2.0")

RETRIEVAL_URL = os.environ.get("RETRIEVAL_URL", "http://localhost:8081")
INFERENCE_URL = os.environ.get("INFERENCE_URL", "http://localhost:8082")
SCHEMA_PATH = os.environ.get("RESPONSE_SCHEMA_PATH", "/app/schemas/response-contract.v1.json")

DATABASE_URL = os.environ.get("DATABASE_URL")  # set in docker compose? (we'll add below)
if not DATABASE_URL:
    # allow query-only mode, but ingest needs DB
    DATABASE_URL = None

SCHEMA = json.loads(open(SCHEMA_PATH, "r", encoding="utf-8").read())
Draft202012Validator.check_schema(SCHEMA)

def sha256b(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()

class QueryRequest(BaseModel):
    org_id: str
    principal_id: str
    mode: str = Field(..., pattern="^(recall|reflection|projection)$")
    query_text: str
    scopes: List[str] = []

class EvidenceSpanIn(BaseModel):
    start_char: int = Field(..., ge=0)
    end_char: int = Field(..., ge=0)
    section_path: str = ""
    confidence: float = Field(0.75, ge=0, le=1)

class IngestRequest(BaseModel):
    org_id: str
    actor_external_subject: str = "p1"     # demo-friendly
    event_type: str = Field(..., minLength=1)
    occurred_at: Optional[str] = None      # ISO8601; optional -> now
    idempotency_key: Optional[str] = None  # recommended
    source_system: str = "demo"
    source_uri: str = "demo://ingest"
    content_type: str = "text/plain"
    text_utf8: str = Field(..., minLength=1)
    spans: Optional[List[EvidenceSpanIn]] = None
    acl_name: str = "public"
    payload: dict = Field(default_factory=dict)
    trace_id: Optional[str] = None

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/v1/query")
async def query(req: QueryRequest):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{RETRIEVAL_URL}/v1/retrieve", json=req.model_dump())
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"retrieval error: {r.text}")
        retrieval = r.json()

        payload = {
            "mode": req.mode,
            "query_text": req.query_text,
            "evidence": retrieval.get("evidence", []),
        }
        i = await client.post(f"{INFERENCE_URL}/v1/infer", json=payload)
        if i.status_code != 200:
            raise HTTPException(status_code=502, detail=f"inference error: {i.text}")
        out = i.json()

    try:
        validate(instance=out, schema=SCHEMA)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway contract validation failed: {e}")

    out["debug"] = {
        **(out.get("debug") or {}),
        "retrieval_debug": retrieval.get("debug", {}),
        "services": {"retrieval": RETRIEVAL_URL, "inference": INFERENCE_URL},
    }
    return out

@app.post("/v1/ingest")
def ingest(req: IngestRequest):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set for gateway (ingest requires DB)")

    occurred_at = datetime.now(timezone.utc) if not req.occurred_at else datetime.fromisoformat(req.occurred_at.replace("Z", "+00:00"))
    text = req.text_utf8

    # If spans not provided, make a simple default: first 240 chars
    spans = req.spans
    if not spans:
        end = min(len(text), 240)
        spans = [EvidenceSpanIn(start_char=0, end_char=end, section_path="auto:0", confidence=0.70)]

    # DB transaction: find actor principal + acl, write artifact + artifact_text + evidence spans + event_log
    with psycopg.connect(DATABASE_URL) as conn, conn.transaction():
        # actor principal
        prow = conn.execute(
            "SELECT principal_id FROM principal WHERE org_id=%s AND external_subject=%s",
            (req.org_id, req.actor_external_subject),
        ).fetchone()
        if not prow:
            # auto-create principal (demo mode; production would be strict)
            principal_id = conn.execute(
                "INSERT INTO principal(org_id, principal_type, external_subject, display_name) "
                "VALUES (%s,'user',%s,%s) RETURNING principal_id",
                (req.org_id, req.actor_external_subject, req.actor_external_subject),
            ).fetchone()[0]
        else:
            principal_id = prow[0]

        # acl
        arow = conn.execute(
            "SELECT acl_id FROM acl WHERE org_id=%s AND name=%s",
            (req.org_id, req.acl_name),
        ).fetchone()
        if not arow:
            acl_id = conn.execute(
                "INSERT INTO acl(org_id, name, description) VALUES (%s,%s,%s) RETURNING acl_id",
                (req.org_id, req.acl_name, "auto-created"),
            ).fetchone()[0]
        else:
            acl_id = arow[0]

        # artifact
        art_id = conn.execute(
            "INSERT INTO artifact(org_id, source_system, source_uri, source_etag, captured_at, occurred_at, "
            "author_principal_id, content_type, storage_uri, sha256, size_bytes, acl_id, pii_classification) "
            "VALUES (%s,%s,%s,NULL,now(),%s,%s,%s,%s,%s,%s,%s,'none') RETURNING artifact_id",
            (
                req.org_id,
                req.source_system,
                req.source_uri,
                occurred_at,
                principal_id,
                req.content_type,
                "s3://demo/ingest",   # placeholder
                sha256b(text),
                len(text),
                acl_id,
            ),
        ).fetchone()[0]

        at_id = conn.execute(
            "INSERT INTO artifact_text(org_id, artifact_id, normaliser_version, language, text_utf8, text_sha256, structure_json) "
            "VALUES (%s,%s,'v1','en',%s,%s,'{}'::jsonb) RETURNING artifact_text_id",
            (req.org_id, art_id, text, sha256b(text)),
        ).fetchone()[0]

        # evidence spans
        for sp in spans:
            if sp.end_char < sp.start_char or sp.end_char > len(text):
                raise HTTPException(status_code=400, detail="Invalid evidence span bounds")
            conn.execute(
                "INSERT INTO evidence_span(org_id, artifact_id, artifact_text_id, span_type, start_char, end_char, "
                "section_path, extracted_by, confidence, created_at) "
                "VALUES (%s,%s,%s,'text',%s,%s,%s,'gateway_ingest',%s,now())",
                (req.org_id, art_id, at_id, sp.start_char, sp.end_char, sp.section_path, sp.confidence),
            )

        # event log
        # idempotency_key is unique per org if provided; allows safe retries
        ev_id = conn.execute(
            "INSERT INTO event_log(org_id, event_type, occurred_at, ingested_at, actor_principal_id, artifact_id, payload, idempotency_key, trace_id) "
            "VALUES (%s,%s,%s,now(),%s,%s,%s::jsonb,%s,%s) "
            "ON CONFLICT (org_id, idempotency_key) DO UPDATE SET ingested_at=EXCLUDED.ingested_at "
            "RETURNING event_id",
            (
                req.org_id,
                req.event_type,
                occurred_at,
                principal_id,
                art_id,
                json.dumps(req.payload or {}),
                req.idempotency_key,
                req.trace_id,
            ),
        ).fetchone()[0]

    return {"ok": True, "event_id": str(ev_id), "artifact_id": str(art_id)}
```

### Update gateway Dockerfile to include psycopg

`services/api-gateway/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 httpx==0.27.2 jsonschema==4.23.0 psycopg[binary]==3.2.1
COPY services/api-gateway/app.py /app/app.py
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 3) Graph deriver service

This is intentionally simple: it takes each unprocessed event, creates/updates a **decision node** + a **topic node**, and connects them to the **artifact node** and each other.

### `services/graph-deriver/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg[binary]==3.2.1
COPY services/graph-deriver/deriver.py /app/deriver.py
ENTRYPOINT ["python", "/app/deriver.py"]
```

### `services/graph-deriver/deriver.py`

```python
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import psycopg

DB = os.environ["DATABASE_URL"]
ORG_ID = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
SLEEP_SECONDS = float(os.environ.get("SLEEP_SECONDS", "1.5"))

def upsert_node(conn, org_id: str, node_type: str, key: str, title: str) -> str:
    row = conn.execute(
        "INSERT INTO graph_node(org_id, node_type, key, title) "
        "VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (org_id, node_type, key) DO UPDATE SET title=EXCLUDED.title "
        "RETURNING node_id::text",
        (org_id, node_type, key, title),
    ).fetchone()
    return row[0]

def upsert_edge(conn, org_id: str, src: str, dst: str, edge_type: str, weight: float = 1.0) -> None:
    conn.execute(
        "INSERT INTO graph_edge(org_id, src_node_id, dst_node_id, edge_type, weight) "
        "VALUES (%s,%s,%s,%s,%s) "
        "ON CONFLICT (org_id, src_node_id, dst_node_id, edge_type) DO UPDATE SET weight=EXCLUDED.weight",
        (org_id, src, dst, edge_type, weight),
    )

def process_one(conn, org_id: str) -> bool:
    # lock one unprocessed event (skip locked so multiple derivers can run)
    row = conn.execute(
        "SELECT event_id::text, event_type, occurred_at, artifact_id::text, payload "
        "FROM event_log "
        "WHERE org_id=%s AND processed_at IS NULL "
        "ORDER BY occurred_at ASC "
        "FOR UPDATE SKIP LOCKED "
        "LIMIT 1",
        (org_id,),
    ).fetchone()

    if not row:
        return False

    event_id, event_type, occurred_at, artifact_id, payload = row
    payload = payload or {}

    # tiny heuristic: derive "topic" from payload.topic or event_type
    topic = payload.get("topic") or event_type
    decision_key = payload.get("decision_key") or f"decision:{event_type}"
    decision_title = payload.get("decision_title") or f"Decision inferred from {event_type}"

    # Build graph nodes
    decision_node = upsert_node(conn, org_id, "decision", decision_key, decision_title)
    topic_node = upsert_node(conn, org_id, "topic", f"topic:{topic}", f"Topic: {topic}")

    # Artifact node (if present)
    if artifact_id:
        art_node = upsert_node(conn, org_id, "artifact", f"artifact:{artifact_id}", f"Artifact {artifact_id[:8]}")
        upsert_edge(conn, org_id, decision_node, art_node, "evidenced_by", 1.0)
        upsert_edge(conn, org_id, art_node, decision_node, "relates", 0.5)

    upsert_edge(conn, org_id, decision_node, topic_node, "relates", 0.8)
    upsert_edge(conn, org_id, topic_node, decision_node, "relates", 0.5)

    # mark processed
    conn.execute("UPDATE event_log SET processed_at=now() WHERE event_id=%s::uuid", (event_id,))
    print(f"processed event {event_id} -> nodes(decision={decision_node}, topic={topic_node})")
    return True

def main():
    while True:
        with psycopg.connect(DB) as conn:
            with conn.transaction():
                did = process_one(conn, ORG_ID)
        if not did:
            time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
```

---

## 4) Wire it into docker compose

Update your `docker-compose.yml`:

### Add `DATABASE_URL` to `api` service, and add `graph-deriver`

```yaml
  api:
    build:
      context: .
      dockerfile: services/api-gateway/Dockerfile
    environment:
      DATABASE_URL: postgres://continuuai:continuuai@postgres:5432/continuuai
      RETRIEVAL_URL: http://retrieval:8080
      INFERENCE_URL: http://inference:8080
      RESPONSE_SCHEMA_PATH: /app/schemas/response-contract.v1.json
    volumes:
      - ./schemas:/app/schemas:ro
    depends_on:
      postgres:
        condition: service_healthy
      retrieval:
        condition: service_started
      inference:
        condition: service_started
    ports:
      - "8080:8080"

  graph-deriver:
    build:
      context: .
      dockerfile: services/graph-deriver/Dockerfile
    environment:
      DATABASE_URL: postgres://continuuai:continuuai@postgres:5432/continuuai
      ORG_ID: "00000000-0000-0000-0000-000000000000"
      SLEEP_SECONDS: "1.0"
    depends_on:
      postgres:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
      seed:
        condition: service_completed_successfully
```

Also create the directory:

```bash
mkdir -p services/graph-deriver
```

---

## 5) Try it: ingest → graph updates → query returns evidence

### Ingest a new decision note

```bash
curl -s http://localhost:8080/v1/ingest -H 'content-type: application/json' -d '{
  "org_id":"00000000-0000-0000-0000-000000000000",
  "actor_external_subject":"p1",
  "event_type":"decision.recorded",
  "idempotency_key":"demo-1",
  "payload":{"topic":"feature_flags","decision_key":"decision:feature_x_flag","decision_title":"Ship Feature X behind a flag"},
  "text_utf8":"Decision: Ship Feature X behind a flag. Rationale: reduce blast radius. Dissent: reliability risk. Mitigation: staged rollout."
}' | jq
```

Give the deriver a second to process, then query:

```bash
curl -s http://localhost:8080/v1/query -H 'content-type: application/json' \
  -d '{"org_id":"00000000-0000-0000-0000-000000000000","principal_id":"p1","mode":"recall","query_text":"What did we decide about Feature X?","scopes":["team:eng"]}' | jq
```

### Inspect the graph

```bash
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c \
"select node_type, key, title from graph_node order by created_at desc limit 20;"
```

```bash
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c \
"select e.edge_type, n1.key as src, n2.key as dst, e.weight from graph_edge e
 join graph_node n1 on n1.node_id=e.src_node_id
 join graph_node n2 on n2.node_id=e.dst_node_id
 order by e.created_at desc limit 20;"
```

---

## What “rebuild the graph deriver” means from here

Right now the deriver is a dumb, honest translator: **event → nodes/edges**. The real version adds two upgrades:

1. **Evidence-backed edges**: every edge should have *which evidence spans justify it* (you’d add an `edge_evidence` join table).

2. **Policy-respecting graph queries**: graph traversal must never surface nodes whose artifacts the principal can’t read (ACL filters become part of scoring, not an afterthought).

If you want the next drop, I’d add:

* `edge_evidence(edge_id, evidence_span_id)` migration
* retrieval service that does: **graph-neighborhood expansion → hybrid score → policy filter → top spans**

That’s where it stops being “RAG with extra steps” and becomes *continuity*.
