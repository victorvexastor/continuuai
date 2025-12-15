ChatGPT said:

Yep. Here’s the next concrete slice: add /v1/ingest to the gateway, persist an event_log row + artifact + artifact_text + evidence_spans, then run a graph-deriver that turns events into a simple decision graph.

Below is copy/paste code for:

    New migrations (DB schema)

    Gateway /v1/ingest (writes event_log + evidence spans)

    Graph deriver service (polls event_log, updates graph tables)

    Docker compose additions (so it runs end-to-end)

1) Migrations

Create these files in migrations/ (in order).
migrations/0001_init.sql

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

migrations/0002_event_log_and_graph.sql

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

2) Add /v1/ingest to the gateway

Replace your services/api-gateway/app.py with the version below (it keeps /v1/query and adds ingest).
services/api-gateway/app.py

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
            "INSERT INTO artifact_text(org_
