Absolutely. Here’s a **copy/pasteable local dev loop**: `docker compose up` boots Postgres, runs migrations, starts **FastAPI gateway**, **retrieval service**, and **inference stub**. The gateway returns a **contract-valid JSON** response, with **evidence spans** coming from the retrieval service (which queries Postgres).

Add these files into your repo (matching paths). Then run:

```bash
docker compose up --build
```

Then hit:

```bash
curl -s http://localhost:8080/v1/query -H 'content-type: application/json' \
  -d '{"org_id":"00000000-0000-0000-0000-000000000000","principal_id":"p1","mode":"recall","query_text":"what did we decide about X?","scopes":["team:eng"]}' | jq
```

---

# 1) `docker-compose.yml` (root)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: continuuai
      POSTGRES_USER: continuuai
      POSTGRES_PASSWORD: continuuai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U continuuai -d continuuai"]
      interval: 2s
      timeout: 2s
      retries: 30

  migrate:
    build:
      context: .
      dockerfile: services/migrate/Dockerfile
    environment:
      DATABASE_URL: postgres://continuuai:continuuai@postgres:5432/continuuai
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./migrations:/app/migrations:ro
    command: ["python", "-m", "migrate_runner", "--migrations", "/app/migrations"]

  seed:
    build:
      context: .
      dockerfile: services/seed/Dockerfile
    environment:
      DATABASE_URL: postgres://continuuai:continuuai@postgres:5432/continuuai
      ORG_ID: "00000000-0000-0000-0000-000000000000"
      ORG_SLUG: "example"
    depends_on:
      migrate:
        condition: service_completed_successfully

  retrieval:
    build:
      context: .
      dockerfile: services/retrieval/Dockerfile
    environment:
      DATABASE_URL: postgres://continuuai:continuuai@postgres:5432/continuuai
      ORG_ID: "00000000-0000-0000-0000-000000000000"
    depends_on:
      postgres:
        condition: service_healthy
      seed:
        condition: service_completed_successfully
    ports:
      - "8081:8080"

  inference:
    build:
      context: .
      dockerfile: services/inference/Dockerfile
    environment:
      RESPONSE_SCHEMA_PATH: /app/schemas/response-contract.v1.json
    volumes:
      - ./schemas:/app/schemas:ro
    ports:
      - "8082:8080"

  api:
    build:
      context: .
      dockerfile: services/api-gateway/Dockerfile
    environment:
      RETRIEVAL_URL: http://retrieval:8080
      INFERENCE_URL: http://inference:8080
      RESPONSE_SCHEMA_PATH: /app/schemas/response-contract.v1.json
    volumes:
      - ./schemas:/app/schemas:ro
    depends_on:
      retrieval:
        condition: service_started
      inference:
        condition: service_started
    ports:
      - "8080:8080"

volumes:
  pgdata: {}
```

---

# 2) Schema: `schemas/response-contract.v1.json`

This is a compact “response contract” that’s strict enough to matter, but not huge.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Continuuai Response Contract v1",
  "type": "object",
  "additionalProperties": false,
  "required": ["contract_version", "mode", "answer", "evidence", "policy", "debug"],
  "properties": {
    "contract_version": { "type": "string", "const": "v1" },
    "mode": { "type": "string", "enum": ["recall", "reflection", "projection"] },
    "answer": { "type": "string", "minLength": 1 },
    "evidence": {
      "type": "array",
      "minItems": 0,
      "maxItems": 20,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["evidence_span_id", "artifact_id", "quote", "confidence"],
        "properties": {
          "evidence_span_id": { "type": "string" },
          "artifact_id": { "type": "string" },
          "quote": { "type": "string", "minLength": 1 },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    },
    "policy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["status", "notes"],
      "properties": {
        "status": { "type": "string", "enum": ["ok", "insufficient_evidence", "policy_denied"] },
        "notes": { "type": "array", "items": { "type": "string" } }
      }
    },
    "debug": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

---

# 3) Migration runner service

## `services/migrate/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg[binary]==3.2.1
COPY services/migrate/migrate_runner.py /app/migrate_runner.py
ENTRYPOINT ["python", "-m", "migrate_runner"]
```

## `services/migrate/migrate_runner.py`

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
import psycopg


def ensure_schema_migrations(conn: psycopg.Connection) -> None:
    conn.execute("""
      CREATE TABLE IF NOT EXISTS schema_migrations (
        filename text PRIMARY KEY,
        applied_at timestamptz NOT NULL DEFAULT now()
      );
    """)


def already_applied(conn: psycopg.Connection, filename: str) -> bool:
    row = conn.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)).fetchone()
    return row is not None


def apply_file(conn: psycopg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with conn.transaction():
        conn.execute(sql)
        conn.execute("INSERT INTO schema_migrations(filename) VALUES (%s)", (path.name,))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrations", required=True, help="Path to migrations dir")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL missing")

    mig_dir = Path(args.migrations)
    files = sorted([p for p in mig_dir.glob("*.sql")], key=lambda p: p.name)

    with psycopg.connect(dsn) as conn:
        ensure_schema_migrations(conn)
        for f in files:
            if already_applied(conn, f.name):
                print(f"skip {f.name}")
                continue
            print(f"apply {f.name}")
            apply_file(conn, f)

    print("migrations complete")


if __name__ == "__main__":
    main()
```

---

# 4) Seed service (creates org, principals, ACLs, evidence)

## `services/seed/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg[binary]==3.2.1
COPY services/seed/seed.py /app/seed.py
ENTRYPOINT ["python", "/app/seed.py"]
```

## `services/seed/seed.py`

```python
from __future__ import annotations
import os
import hashlib
from datetime import datetime, timezone

import psycopg


def sha256b(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()


def main() -> None:
    dsn = os.environ["DATABASE_URL"]
    org_id = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
    org_slug = os.environ.get("ORG_SLUG", "example")

    with psycopg.connect(dsn) as conn, conn.transaction():
        # Org (explicit id so demo requests can hardcode it)
        conn.execute(
            "INSERT INTO org(org_id, org_slug, display_name) VALUES (%s,%s,%s) "
            "ON CONFLICT (org_id) DO NOTHING",
            (org_id, org_slug, "Example Org"),
        )

        # Roles
        conn.execute(
            "INSERT INTO role(org_id, role_name) VALUES (%s,'admin') ON CONFLICT DO NOTHING",
            (org_id,),
        )
        conn.execute(
            "INSERT INTO role(org_id, role_name) VALUES (%s,'staff') ON CONFLICT DO NOTHING",
            (org_id,),
        )

        # Principals
        conn.execute(
            "INSERT INTO principal(org_id, principal_type, external_subject, display_name) "
            "VALUES (%s,'user','p1','Pilot One') ON CONFLICT DO NOTHING",
            (org_id,),
        )

        # ACLs
        acl_public = conn.execute(
            "INSERT INTO acl(org_id, name, description) VALUES (%s,'public','Demo public ACL') "
            "ON CONFLICT (org_id, name) DO UPDATE SET description=EXCLUDED.description "
            "RETURNING acl_id",
            (org_id,),
        ).fetchone()[0]

        # allow principal p1 on acl_public
        principal_id = conn.execute(
            "SELECT principal_id FROM principal WHERE org_id=%s AND external_subject='p1'",
            (org_id,),
        ).fetchone()[0]

        conn.execute(
            "INSERT INTO acl_allow(org_id, acl_id, allow_type, principal_id, role_id) "
            "VALUES (%s,%s,'principal',%s,NULL) "
            "ON CONFLICT DO NOTHING",
            (org_id, acl_public, principal_id),
        )

        # Artifacts + text
        artifact_id = conn.execute(
            "INSERT INTO artifact(org_id, source_system, source_uri, source_etag, captured_at, occurred_at, "
            "author_principal_id, content_type, storage_uri, sha256, size_bytes, acl_id, pii_classification) "
            "VALUES (%s,'demo','demo://artifact/1','v1',now(),now(),%s,'text/plain','s3://demo/1',%s,123,%s,'none') "
            "RETURNING artifact_id",
            (org_id, principal_id, sha256b("artifact1"), acl_public),
        ).fetchone()[0]

        atid = conn.execute(
            "INSERT INTO artifact_text(org_id, artifact_id, normaliser_version, language, text_utf8, text_sha256, structure_json) "
            "VALUES (%s,%s,'v1','en',%s,%s,'{}'::jsonb) RETURNING artifact_text_id",
            (
                org_id,
                artifact_id,
                "Decision log: We decided to ship Feature X behind a flag.\n"
                "Dissent: Reliability risk noted; mitigation: staged rollout.\n"
                "Outcome: mixed; rollback once, then fixed.\n",
                sha256b("text1"),
            ),
        ).fetchone()[0]

        # Evidence spans (3 small spans)
        now = datetime.now(timezone.utc)
        spans = [
            ("Decision confirmed: ship Feature X behind a flag.", 0, 52, 0.92, "a1|sec1"),
            ("Dissent: reliability risk; mitigation: staged rollout.", 53, 110, 0.84, "a1|sec1"),
            ("Outcome: mixed; rollback once, then fixed.", 111, 156, 0.78, "a1|sec2"),
        ]
        for i, (txt, s, e, conf, skey) in enumerate(spans, start=1):
            conn.execute(
                "INSERT INTO evidence_span(org_id, artifact_id, artifact_text_id, span_type, start_char, end_char, "
                "section_path, extracted_by, confidence, created_at) "
                "VALUES (%s,%s,%s,'text',%s,%s,%s,'seed',%s,now())",
                (org_id, artifact_id, atid, s, e, skey, conf),
            )

    print("seed complete")


if __name__ == "__main__":
    main()
```

---

# 5) Retrieval service (FastAPI, reads evidence from Postgres)

## `services/retrieval/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 psycopg[binary]==3.2.1
COPY services/retrieval/app.py /app/app.py
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## `services/retrieval/app.py`

```python
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
import psycopg

app = FastAPI(title="Continuuai Retrieval", version="0.1.0")

DB = os.environ["DATABASE_URL"]

class RetrievalRequest(BaseModel):
    org_id: str
    principal_id: str
    mode: str = Field(..., pattern="^(recall|reflection|projection)$")
    query_text: str
    scopes: List[str] = []

class EvidenceOut(BaseModel):
    evidence_span_id: str
    artifact_id: str
    quote: str
    confidence: float

class RetrievalResponse(BaseModel):
    evidence: List[EvidenceOut]
    debug: dict

@app.post("/v1/retrieve", response_model=RetrievalResponse)
def retrieve(req: RetrievalRequest) -> RetrievalResponse:
    # This is intentionally “boring”: just return the top evidence spans we have.
    # Later: plug in your scorer + hybrid ranker + graph signals.
    q = """
      SELECT
        evidence_span_id::text,
        artifact_id::text,
        confidence,
        section_path,
        start_char,
        end_char
      FROM evidence_span
      WHERE org_id = %s
      ORDER BY created_at DESC
      LIMIT 8;
    """

    with psycopg.connect(DB) as conn:
        rows = conn.execute(q, (req.org_id,)).fetchall()

        # Pull artifact_text so we can slice quotes.
        # In real life you pre-store the exact snippet; this is a demo.
        trow = conn.execute("""
          SELECT at.text_utf8
          FROM artifact_text at
          JOIN evidence_span es ON es.artifact_text_id = at.artifact_text_id
          WHERE es.org_id = %s
          LIMIT 1
        """, (req.org_id,)).fetchone()

        full_text = trow[0] if trow else ""

    evidence = []
    for evid, art, conf, skey, s, e in rows:
        quote = full_text[s:e] if full_text and s is not None and e is not None else "(no text)"
        evidence.append(EvidenceOut(
            evidence_span_id=evid,
            artifact_id=art,
            quote=quote.strip(),
            confidence=float(conf),
        ))

    return RetrievalResponse(
        evidence=evidence,
        debug={"mode": req.mode, "count": len(evidence)}
    )
```

---

# 6) Inference stub (FastAPI, validates contract JSON)

## `services/inference/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 jsonschema==4.23.0
COPY services/inference/app.py /app/app.py
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## `services/inference/app.py`

```python
from __future__ import annotations

import json
import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from jsonschema import validate, Draft202012Validator

app = FastAPI(title="Continuuai Inference Stub", version="0.1.0")

SCHEMA_PATH = os.environ.get("RESPONSE_SCHEMA_PATH", "/app/schemas/response-contract.v1.json")
SCHEMA = json.loads(open(SCHEMA_PATH, "r", encoding="utf-8").read())
Draft202012Validator.check_schema(SCHEMA)

class EvidenceIn(BaseModel):
    evidence_span_id: str
    artifact_id: str
    quote: str
    confidence: float = Field(..., ge=0, le=1)

class InferRequest(BaseModel):
    mode: str = Field(..., pattern="^(recall|reflection|projection)$")
    query_text: str
    evidence: List[EvidenceIn]

@app.post("/v1/infer")
def infer(req: InferRequest):
    # A “model” that is stubbornly contract-first and evidence-anchored.
    # Later: replace with real LLM call + strict JSON decoding.
    top = req.evidence[:3]
    if not top:
        out = {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": "I don’t have sufficient evidence in the current memory slice to answer that safely.",
            "evidence": [],
            "policy": {"status": "insufficient_evidence", "notes": ["no_evidence_returned"]},
            "debug": {"stub": True}
        }
    else:
        bullet_quotes = " ".join([f"[{i+1}] {e.quote}" for i, e in enumerate(top)])
        out = {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": f"Based on the available evidence, here’s what we previously recorded: {bullet_quotes}",
            "evidence": [e.model_dump() for e in top],
            "policy": {"status": "ok", "notes": ["stub_inference", "evidence_anchored"]},
            "debug": {"stub": True, "evidence_count_in": len(req.evidence)}
        }

    # Contract validation (hard gate)
    try:
        validate(instance=out, schema=SCHEMA)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contract validation failed: {e}")

    return out
```

---

# 7) Tiny FastAPI gateway (end-to-end orchestration)

## `services/api-gateway/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 httpx==0.27.2 jsonschema==4.23.0
COPY services/api-gateway/app.py /app/app.py
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## `services/api-gateway/app.py`

```python
from __future__ import annotations

import json
import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
from jsonschema import validate, Draft202012Validator

app = FastAPI(title="Continuuai API Gateway", version="0.1.0")

RETRIEVAL_URL = os.environ.get("RETRIEVAL_URL", "http://localhost:8081")
INFERENCE_URL = os.environ.get("INFERENCE_URL", "http://localhost:8082")
SCHEMA_PATH = os.environ.get("RESPONSE_SCHEMA_PATH", "/app/schemas/response-contract.v1.json")

SCHEMA = json.loads(open(SCHEMA_PATH, "r", encoding="utf-8").read())
Draft202012Validator.check_schema(SCHEMA)

class QueryRequest(BaseModel):
    org_id: str
    principal_id: str
    mode: str = Field(..., pattern="^(recall|reflection|projection)$")
    query_text: str
    scopes: List[str] = []

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/v1/query")
async def query(req: QueryRequest):
    async with httpx.AsyncClient(timeout=20) as client:
        # 1) Retrieve evidence
        r = await client.post(f"{RETRIEVAL_URL}/v1/retrieve", json=req.model_dump())
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"retrieval error: {r.text}")
        retrieval = r.json()

        # 2) Inference (contract JSON)
        payload = {
            "mode": req.mode,
            "query_text": req.query_text,
            "evidence": retrieval.get("evidence", []),
        }
        i = await client.post(f"{INFERENCE_URL}/v1/infer", json=payload)
        if i.status_code != 200:
            raise HTTPException(status_code=502, detail=f"inference error: {i.text}")
        out = i.json()

    # 3) Validate contract again at the boundary (paranoid by design)
    try:
        validate(instance=out, schema=SCHEMA)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway contract validation failed: {e}")

    # 4) Attach retrieval debug (allowed by schema via debug.additionalProperties)
    out["debug"] = {
        **(out.get("debug") or {}),
        "retrieval_debug": retrieval.get("debug", {}),
        "services": {"retrieval": RETRIEVAL_URL, "inference": INFERENCE_URL},
    }
    return out
```

---

# 8) Minor `.gitignore` (root)

```gitignore
__pycache__/
*.pyc
pgdata/
.env
```

---

# 9) You’ll need these extra directories

Create these empty dirs if they don’t exist yet:

```bash
mkdir -p schemas services/{api-gateway,inference,migrate,seed,retrieval}
```

---

## Notes on why this is a good “first ritual”

* It proves the **shape** of the system: memory → evidence → contract response.
* It’s **hard-gated** by JSON Schema at inference and again at the gateway.
* You can now replace retrieval logic (hybrid scoring, ACL filtering, graph signals) and inference logic (LLM) without changing the product’s “truth interface”.

Next natural step: add `/v1/ingest` to the gateway that writes an `event_log` row + evidence spans, then rebuild the graph deriver. That’s where the “continuity engine” becomes obviously real.
