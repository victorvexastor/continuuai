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

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
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
    actor_external_subject: str = "p1"
    event_type: str = Field(..., minLength=1)
    occurred_at: Optional[str] = None
    idempotency_key: Optional[str] = None
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

    spans = req.spans
    if not spans:
        end = min(len(text), 240)
        spans = [EvidenceSpanIn(start_char=0, end_char=end, section_path="auto:0", confidence=0.70)]

    with psycopg.connect(DATABASE_URL) as conn, conn.transaction():
        prow = conn.execute(
            "SELECT principal_id FROM principal WHERE org_id=%s AND external_subject=%s",
            (req.org_id, req.actor_external_subject),
        ).fetchone()
        if not prow:
            principal_id = conn.execute(
                "INSERT INTO principal(org_id, principal_type, external_subject, display_name) "
                "VALUES (%s,'user',%s,%s) RETURNING principal_id",
                (req.org_id, req.actor_external_subject, req.actor_external_subject),
            ).fetchone()[0]
        else:
            principal_id = prow[0]

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
                "s3://demo/ingest",
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

        for sp in spans:
            if sp.end_char < sp.start_char or sp.end_char > len(text):
                raise HTTPException(status_code=400, detail="Invalid evidence span bounds")
            conn.execute(
                "INSERT INTO evidence_span(org_id, artifact_id, artifact_text_id, span_type, start_char, end_char, "
                "section_path, extracted_by, confidence, created_at) "
                "VALUES (%s,%s,%s,'text',%s,%s,%s,'gateway_ingest',%s,now())",
                (req.org_id, art_id, at_id, sp.start_char, sp.end_char, sp.section_path, sp.confidence),
            )

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
