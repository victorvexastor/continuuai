from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jsonschema import Draft202012Validator, validate
from pydantic import BaseModel, Field

app = FastAPI(title="Continuuai API Gateway", version="0.2.0")

# CORS configuration
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class DissentIn(BaseModel):
    person: str
    concern: str
    reasoning: str = ""

class UncertaintyIn(BaseModel):
    aspect: str
    description: str
    impact_if_wrong: str = ""
    mitigation: str = ""

class AlternativeIn(BaseModel):
    option: str
    why_rejected: str

class DecisionRequest(BaseModel):
    org_id: str = "00000000-0000-0000-0000-000000000000"
    principal_id: str = "ad4e8240-683e-40a8-a00d-6d5c7c5bb32b"
    stream_id: str
    title: str = Field(..., min_length=1)
    what_decided: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1)
    constraints: List[str] = []
    alternatives: List[AlternativeIn] = []
    dissent: List[DissentIn] = []
    uncertainty: List[UncertaintyIn] = []
    revisit_date: Optional[str] = None

class StreamCreateRequest(BaseModel):
    org_id: str = "00000000-0000-0000-0000-000000000000"
    name: str = Field(..., min_length=1)
    description: str = ""
    color: str = "#6366f1"

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/v1/query")
async def query(req: QueryRequest):
    # Extended timeout for LLM inference (120b model on CPU/GPU hybrid can be slow)
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{RETRIEVAL_URL}/v1/retrieve", json=req.model_dump())
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"retrieval error: {r.text}")
        retrieval = r.json()

        # Map retrieval results to inference evidence format
        retrieval_results = retrieval.get("results", [])
        evidence = [
            {
                "evidence_span_id": r.get("id", ""),
                "artifact_id": r.get("artifact_id", ""),
                "quote": r.get("text", ""),
                "confidence": r.get("confidence", 0.75),
                "occurred_at": r.get("created_at", ""),
            }
            for r in retrieval_results
        ]
        
        payload = {
            "mode": req.mode,
            "query_text": req.query_text,
            "evidence": evidence,
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

# ============ STREAMS API ============

@app.get("/v1/streams")
def list_streams(org_id: str = "00000000-0000-0000-0000-000000000000"):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT stream_id, stream_name, description, 
                      COALESCE(color, '#6366f1') as color,
                      COALESCE(status, 'active') as status,
                      (SELECT COUNT(*) FROM decision d WHERE d.stream_id = ds.stream_id) as decision_count
               FROM decision_stream ds 
               WHERE org_id=%s AND (archived_at IS NULL OR status = 'active')
               ORDER BY stream_name""",
            (org_id,)
        ).fetchall()
    
    return {
        "streams": [
            {
                "id": str(row[0]), 
                "name": row[1], 
                "description": row[2] or "",
                "color": row[3],
                "status": row[4],
                "decision_count": row[5]
            }
            for row in rows
        ]
    }

@app.post("/v1/streams")
def create_stream(req: StreamCreateRequest):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn, conn.transaction():
        row = conn.execute(
            """INSERT INTO decision_stream (org_id, stream_name, description, color, status)
               VALUES (%s, %s, %s, %s, 'active')
               ON CONFLICT (org_id, stream_name) DO UPDATE SET description = EXCLUDED.description
               RETURNING stream_id""",
            (req.org_id, req.name, req.description, req.color)
        ).fetchone()
    
    return {"ok": True, "stream_id": str(row[0])}

# ============ DECISIONS API ============

@app.get("/v1/decisions")
def list_decisions(
    org_id: str = "00000000-0000-0000-0000-000000000000",
    stream_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn:
        query = """
            SELECT d.decision_id, d.title, d.what_decided, d.reasoning, d.decided_at,
                   d.status, d.revisit_date, ds.stream_name, ds.color,
                   p.display_name as decided_by_name,
                   (SELECT COUNT(*) FROM dissent_record dr WHERE dr.decision_id = d.decision_id AND dr.status = 'open') as open_dissent,
                   (SELECT COUNT(*) FROM uncertainty_record ur WHERE ur.decision_id = d.decision_id AND ur.status = 'open') as open_uncertainty
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            JOIN principal p ON d.decided_by = p.principal_id
            WHERE d.org_id = %s
        """
        params = [org_id]
        
        if stream_id:
            query += " AND d.stream_id = %s"
            params.append(stream_id)
        if status:
            query += " AND d.status = %s"
            params.append(status)
        
        query += " ORDER BY d.decided_at DESC LIMIT %s"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
    
    return {
        "decisions": [
            {
                "id": str(row[0]),
                "title": row[1],
                "what_decided": row[2],
                "reasoning": row[3][:200] + "..." if len(row[3]) > 200 else row[3],
                "decided_at": row[4].isoformat() if row[4] else None,
                "status": row[5],
                "revisit_date": str(row[6]) if row[6] else None,
                "stream": {"name": row[7], "color": row[8]},
                "decided_by": row[9],
                "open_dissent_count": row[10],
                "open_uncertainty_count": row[11]
            }
            for row in rows
        ]
    }

@app.get("/v1/decisions/{decision_id}")
def get_decision(decision_id: str, org_id: str = "00000000-0000-0000-0000-000000000000"):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn:
        # Get decision
        row = conn.execute(
            """
            SELECT d.decision_id, d.title, d.what_decided, d.reasoning, 
                   d.constraints_at_time, d.alternatives_considered,
                   d.decided_at, d.status, d.revisit_date,
                   ds.stream_id, ds.stream_name, ds.color,
                   p.principal_id, p.display_name
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            JOIN principal p ON d.decided_by = p.principal_id
            WHERE d.decision_id = %s AND d.org_id = %s
            """,
            (decision_id, org_id)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Decision not found")
        
        # Get dissent records
        dissent_rows = conn.execute(
            """SELECT dissent_id, dissenter_name, concern, reasoning, status, resolution
               FROM dissent_record WHERE decision_id = %s ORDER BY created_at""",
            (decision_id,)
        ).fetchall()
        
        # Get uncertainty records
        uncertainty_rows = conn.execute(
            """SELECT uncertainty_id, aspect, description, impact_if_wrong, mitigation, status, resolution
               FROM uncertainty_record WHERE decision_id = %s ORDER BY created_at""",
            (decision_id,)
        ).fetchall()
        
        # Get outcomes
        outcome_rows = conn.execute(
            """SELECT outcome_id, outcome_type, description, lessons_learned, recorded_at
               FROM decision_outcome WHERE decision_id = %s ORDER BY recorded_at DESC""",
            (decision_id,)
        ).fetchall()
    
    return {
        "id": str(row[0]),
        "title": row[1],
        "what_decided": row[2],
        "reasoning": row[3],
        "constraints": row[4] or [],
        "alternatives": row[5] or [],
        "decided_at": row[6].isoformat() if row[6] else None,
        "status": row[7],
        "revisit_date": str(row[8]) if row[8] else None,
        "stream": {
            "id": str(row[9]),
            "name": row[10],
            "color": row[11]
        },
        "decided_by": {
            "id": str(row[12]),
            "name": row[13]
        },
        "dissent": [
            {
                "id": str(d[0]),
                "person": d[1],
                "concern": d[2],
                "reasoning": d[3],
                "status": d[4],
                "resolution": d[5]
            }
            for d in dissent_rows
        ],
        "uncertainty": [
            {
                "id": str(u[0]),
                "aspect": u[1],
                "description": u[2],
                "impact_if_wrong": u[3],
                "mitigation": u[4],
                "status": u[5],
                "resolution": u[6]
            }
            for u in uncertainty_rows
        ],
        "outcomes": [
            {
                "id": str(o[0]),
                "type": o[1],
                "description": o[2],
                "lessons_learned": o[3],
                "recorded_at": o[4].isoformat() if o[4] else None
            }
            for o in outcome_rows
        ]
    }

@app.post("/v1/decisions")
def record_decision(req: DecisionRequest):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    decided_at = datetime.now(timezone.utc)
    revisit_date = None
    if req.revisit_date:
        try:
            revisit_date = datetime.strptime(req.revisit_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    with psycopg.connect(DATABASE_URL) as conn, conn.transaction():
        # Insert the decision
        decision_row = conn.execute(
            """
            INSERT INTO decision (
                org_id, stream_id, title, what_decided, reasoning,
                constraints_at_time, alternatives_considered,
                decided_by, decided_at, revisit_date
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
            RETURNING decision_id
            """,
            (
                req.org_id,
                req.stream_id,
                req.title,
                req.what_decided,
                req.reasoning,
                json.dumps(req.constraints),
                json.dumps([a.model_dump() for a in req.alternatives]),
                req.principal_id,
                decided_at,
                revisit_date
            )
        ).fetchone()
        decision_id = decision_row[0]
        
        # Insert dissent records
        for d in req.dissent:
            conn.execute(
                """
                INSERT INTO dissent_record (org_id, decision_id, dissenter_name, concern, reasoning)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (req.org_id, decision_id, d.person, d.concern, d.reasoning)
            )
        
        # Insert uncertainty records
        for u in req.uncertainty:
            conn.execute(
                """
                INSERT INTO uncertainty_record (org_id, decision_id, aspect, description, impact_if_wrong, mitigation)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (req.org_id, decision_id, u.aspect, u.description, u.impact_if_wrong, u.mitigation)
            )
        
        # Create artifact and evidence spans for retrieval
        combined_text = f"{req.title}\n\n{req.what_decided}\n\nReasoning: {req.reasoning}"
        
        art_id = conn.execute(
            """
            INSERT INTO artifact(
                org_id, source_system, source_uri, captured_at, occurred_at,
                author_principal_id, content_type, storage_uri, sha256, size_bytes,
                acl_id, pii_classification, stream_id
            )
            VALUES (
                %s, 'decision', %s, now(), %s, %s, 'text/plain', 'internal', %s, %s,
                (SELECT acl_id FROM acl WHERE org_id=%s AND name='public' LIMIT 1),
                'none', %s
            )
            RETURNING artifact_id
            """,
            (
                req.org_id,
                f"decision://{decision_id}",
                decided_at,
                req.principal_id,
                sha256b(combined_text),
                len(combined_text),
                req.org_id,
                req.stream_id
            )
        ).fetchone()[0]
        
        # Update decision with artifact link
        conn.execute(
            "UPDATE decision SET artifact_id = %s WHERE decision_id = %s",
            (art_id, decision_id)
        )
        
        # Insert artifact_text for search
        at_id = conn.execute(
            """
            INSERT INTO artifact_text(org_id, artifact_id, normaliser_version, language, text_utf8, text_sha256, structure_json)
            VALUES (%s, %s, 'v1', 'en', %s, %s, '{}'::jsonb)
            RETURNING artifact_text_id
            """,
            (req.org_id, art_id, combined_text, sha256b(combined_text))
        ).fetchone()[0]
        
        # Create evidence span for the whole decision
        conn.execute(
            """
            INSERT INTO evidence_span(org_id, artifact_id, artifact_text_id, span_type, start_char, end_char, section_path, extracted_by, confidence)
            VALUES (%s, %s, %s, 'text', 0, %s, 'decision', 'decision_record', 1.0)
            """,
            (req.org_id, art_id, at_id, len(combined_text))
        )
        
        # Log event
        ev_id = conn.execute(
            """
            INSERT INTO event_log(org_id, event_type, occurred_at, ingested_at, actor_principal_id, artifact_id, payload)
            VALUES (%s, 'decision_recorded', %s, now(), %s, %s, %s::jsonb)
            RETURNING event_id
            """,
            (
                req.org_id,
                decided_at,
                req.principal_id,
                art_id,
                json.dumps({
                    "decision_id": str(decision_id),
                    "stream_id": req.stream_id,
                    "title": req.title,
                    "has_dissent": len(req.dissent) > 0,
                    "has_uncertainty": len(req.uncertainty) > 0,
                    "revisit_date": req.revisit_date
                })
            )
        ).fetchone()[0]
    
    return {
        "ok": True,
        "decision_id": str(decision_id),
        "artifact_id": str(art_id),
        "event_id": str(ev_id)
    }

# ============ INSIGHTS API (Dashboard) ============

@app.get("/v1/insights")
def list_insights(
    org_id: str = "00000000-0000-0000-0000-000000000000",
    status: str = "active"
):
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """
            SELECT insight_id, insight_type, severity, title, description, decision_ids, created_at
            FROM insight
            WHERE org_id = %s AND status = %s
            ORDER BY 
                CASE severity WHEN 'attention' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
                created_at DESC
            LIMIT 20
            """,
            (org_id, status)
        ).fetchall()
    
    return {
        "insights": [
            {
                "id": str(row[0]),
                "type": row[1],
                "severity": row[2],
                "title": row[3],
                "description": row[4],
                "decision_ids": [str(d) for d in (row[5] or [])],
                "created_at": row[6].isoformat() if row[6] else None
            }
            for row in rows
        ]
    }

@app.get("/v1/dashboard")
def get_dashboard(org_id: str = "00000000-0000-0000-0000-000000000000"):
    """Dashboard endpoint: returns needs-attention items, recent decisions, and stats."""
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    with psycopg.connect(DATABASE_URL) as conn:
        # Decisions due for revisit
        revisit_due = conn.execute(
            """
            SELECT decision_id, title, revisit_date, ds.stream_name
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            WHERE d.org_id = %s AND d.status = 'active' 
                  AND d.revisit_date IS NOT NULL AND d.revisit_date <= CURRENT_DATE
            ORDER BY revisit_date
            LIMIT 5
            """,
            (org_id,)
        ).fetchall()
        
        # Open dissent
        open_dissent = conn.execute(
            """
            SELECT dr.dissent_id, d.decision_id, d.title, dr.dissenter_name, dr.concern, ds.stream_name
            FROM dissent_record dr
            JOIN decision d ON dr.decision_id = d.decision_id
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            WHERE dr.org_id = %s AND dr.status = 'open'
            ORDER BY dr.created_at DESC
            LIMIT 5
            """,
            (org_id,)
        ).fetchall()
        
        # Active insights
        insights = conn.execute(
            """
            SELECT insight_id, insight_type, severity, title, description
            FROM insight
            WHERE org_id = %s AND status = 'active'
            ORDER BY CASE severity WHEN 'attention' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END
            LIMIT 5
            """,
            (org_id,)
        ).fetchall()
        
        # Recent decisions
        recent = conn.execute(
            """
            SELECT d.decision_id, d.title, d.decided_at, ds.stream_name, ds.color, p.display_name
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            JOIN principal p ON d.decided_by = p.principal_id
            WHERE d.org_id = %s
            ORDER BY d.decided_at DESC
            LIMIT 10
            """,
            (org_id,)
        ).fetchall()
        
        # Stats
        stats = conn.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM decision WHERE org_id = %s) as total_decisions,
                (SELECT COUNT(*) FROM decision WHERE org_id = %s AND status = 'active') as active_decisions,
                (SELECT COUNT(*) FROM dissent_record WHERE org_id = %s AND status = 'open') as open_dissent,
                (SELECT COUNT(*) FROM decision WHERE org_id = %s AND revisit_date <= CURRENT_DATE AND status = 'active') as revisit_due
            """,
            (org_id, org_id, org_id, org_id)
        ).fetchone()
    
    needs_attention = []
    
    # Add revisit due items
    for row in revisit_due:
        needs_attention.append({
            "type": "revisit_due",
            "severity": "warning",
            "title": f"Decision due for revisit: {row[1]}",
            "description": f"Was scheduled for {row[2]}",
            "decision_id": str(row[0]),
            "stream": row[3]
        })
    
    # Add open dissent items
    for row in open_dissent:
        needs_attention.append({
            "type": "unresolved_dissent",
            "severity": "attention",
            "title": f"Unresolved dissent on: {row[2]}",
            "description": f"{row[3]}'s concern: {row[4][:100]}...",
            "decision_id": str(row[1]),
            "stream": row[5]
        })
    
    # Add insights
    for row in insights:
        needs_attention.append({
            "type": row[1],
            "severity": row[2],
            "title": row[3],
            "description": row[4],
            "insight_id": str(row[0])
        })
    
    return {
        "needs_attention": needs_attention[:10],  # Limit to top 10
        "recent_decisions": [
            {
                "id": str(row[0]),
                "title": row[1],
                "decided_at": row[2].isoformat() if row[2] else None,
                "stream": {"name": row[3], "color": row[4]},
                "decided_by": row[5]
            }
            for row in recent
        ],
        "stats": {
            "total_decisions": stats[0],
            "active_decisions": stats[1],
            "open_dissent": stats[2],
            "revisit_due": stats[3]
        }
    }
