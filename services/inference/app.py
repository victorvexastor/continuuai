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
    # A "model" that is stubbornly contract-first and evidence-anchored.
    # Later: replace with real LLM call + strict JSON decoding.
    top = req.evidence[:3]
    if not top:
        out = {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": "I don't have sufficient evidence in the current memory slice to answer that safely.",
            "evidence": [],
            "policy": {"status": "insufficient_evidence", "notes": ["no_evidence_returned"]},
            "debug": {"stub": True}
        }
    else:
        bullet_quotes = " ".join([f"[{i+1}] {e.quote}" for i, e in enumerate(top)])
        out = {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": f"Based on the available evidence, here's what we previously recorded: {bullet_quotes}",
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
