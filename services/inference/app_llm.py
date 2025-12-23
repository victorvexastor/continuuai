"""
ContinuuAI Inference Service with llama.cpp integration
Uses gpt-oss-120b with GPU offload + CPU for evidence-anchored responses
"""
from __future__ import annotations

import json
import os
import re
import logging
import httpx
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from jsonschema import validate, Draft202012Validator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("inference")

app = FastAPI(title="ContinuuAI Inference", version="0.2.0")

# Configuration
SCHEMA_PATH = os.environ.get("RESPONSE_SCHEMA_PATH", "/app/schemas/response-contract.v1.json")
LLAMA_SERVER_URL = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8084")
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1024"))
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
USE_STUB = os.environ.get("USE_STUB", "false").lower() == "true"

# Load schema
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


def build_prompt(mode: str, query: str, evidence: List[EvidenceIn]) -> str:
    """Build evidence-anchored prompt for the LLM"""
    
    evidence_text = ""
    for i, e in enumerate(evidence[:5], 1):  # Top 5 evidence
        evidence_text += f"[{i}] (confidence: {e.confidence:.0%}) \"{e.quote}\"\n"
    
    if mode == "recall":
        system = """You are ContinuuAI, an organizational memory assistant. 
Your task is to answer questions based ONLY on the provided evidence.
Rules:
- ONLY use information from the evidence provided
- Cite evidence using [1], [2], etc.
- If evidence is insufficient, say so
- Never make up information
- Be concise and direct"""
        
        prompt = f"""<|system|>
{system}
<|user|>
Question: {query}

Available Evidence:
{evidence_text if evidence_text else "No evidence available."}

Based on this evidence, provide a clear answer:
<|assistant|>"""

    elif mode == "reflection":
        system = """You are ContinuuAI, analyzing organizational patterns.
Your task is to identify tensions, contradictions, or patterns in decisions.
Rules:
- Point out conflicts between decisions
- Note assumption changes over time
- Identify recurring patterns
- Cite evidence using [1], [2], etc."""
        
        prompt = f"""<|system|>
{system}
<|user|>
Analyze this context for patterns or tensions: {query}

Evidence to analyze:
{evidence_text if evidence_text else "No evidence available."}

Reflection:
<|assistant|>"""

    else:  # projection
        system = """You are ContinuuAI, projecting possible futures based on organizational history.
Your task is to describe likely scenarios if current patterns continue.
Rules:
- Base projections on historical evidence only
- Present multiple scenarios when appropriate
- Note uncertainties explicitly
- Cite evidence using [1], [2], etc."""
        
        prompt = f"""<|system|>
{system}
<|user|>
Based on our history, what might happen with: {query}

Historical evidence:
{evidence_text if evidence_text else "No evidence available."}

Projection:
<|assistant|>"""

    return prompt


def cleanup_llm_output(raw: str) -> str:
    """Clean up LLM output by removing internal tags and formatting."""
    # Remove <|...|> style internal reasoning tags and their content
    # Pattern: from <|xxx|> up to the next <|final|> or <|end|> or start of actual answer
    text = raw
    
    # Remove blocks like <|analysis|>...<|end|> or <|channel|>...|>
    text = re.sub(r'<\|[^|]+\|>[^<]*(?=<\||$)', '', text, flags=re.DOTALL)
    
    # Remove any remaining <|...|> tags
    text = re.sub(r'<\|[^|]+\|>', '', text)
    
    # Remove things like "analysis|>" or "final|>" 
    text = re.sub(r'\b\w+\|>', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


async def call_llama_server(prompt: str) -> str:
    """Call llama-server completion endpoint"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{LLAMA_SERVER_URL}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "stop": ["<|user|>", "<|system|>", "\n\n\n"],
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
            raw = result.get("content", "").strip()
            return cleanup_llm_output(raw)
    except httpx.TimeoutException:
        logger.error("LLM request timed out")
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except httpx.HTTPError as e:
        logger.error(f"LLM request failed: {e}")
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")


def stub_response(req: InferRequest) -> dict:
    """Fallback stub response when LLM is unavailable"""
    top = req.evidence[:3]
    if not top:
        return {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": "I don't have sufficient evidence in the current memory slice to answer that safely.",
            "evidence": [],
            "policy": {"status": "insufficient_evidence", "notes": ["no_evidence_returned"]},
            "debug": {"stub": True}
        }
    else:
        bullet_quotes = " ".join([f"[{i+1}] {e.quote}" for i, e in enumerate(top)])
        return {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": f"Based on the available evidence, here's what we previously recorded: {bullet_quotes}",
            "evidence": [e.model_dump() for e in top],
            "policy": {"status": "ok", "notes": ["stub_inference", "evidence_anchored"]},
            "debug": {"stub": True, "evidence_count_in": len(req.evidence)}
        }


@app.get("/healthz")
async def healthz():
    """Health check - also checks LLM availability"""
    llm_status = "unknown"
    if not USE_STUB:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{LLAMA_SERVER_URL}/health")
                llm_status = "ok" if r.status_code == 200 else "unavailable"
        except:
            llm_status = "unavailable"
    return {"ok": True, "llm_status": llm_status, "stub_mode": USE_STUB}


@app.post("/v1/infer")
async def infer(req: InferRequest):
    """Main inference endpoint - evidence-anchored responses"""
    
    # Use stub if configured or if no evidence
    if USE_STUB:
        out = stub_response(req)
    elif not req.evidence:
        out = {
            "contract_version": "v1",
            "mode": req.mode,
            "answer": "I don't have sufficient evidence in the current memory slice to answer that safely.",
            "evidence": [],
            "policy": {"status": "insufficient_evidence", "notes": ["no_evidence_provided"]},
            "debug": {"stub": False, "reason": "no_evidence"}
        }
    else:
        # Build prompt and call LLM
        prompt = build_prompt(req.mode, req.query_text, req.evidence)
        logger.info(f"Calling LLM for {req.mode} query with {len(req.evidence)} evidence items")
        
        try:
            answer = await call_llama_server(prompt)
            
            # Build evidence list for response
            evidence_out = [e.model_dump() for e in req.evidence[:5]]
            
            out = {
                "contract_version": "v1",
                "mode": req.mode,
                "answer": answer,
                "evidence": evidence_out,
                "policy": {"status": "ok", "notes": ["llm_inference", "evidence_anchored"]},
                "debug": {
                    "stub": False,
                    "evidence_count_in": len(req.evidence),
                    "model": "gemma-3-27b-it",
                    "temperature": TEMPERATURE
                }
            }
        except HTTPException:
            # LLM failed - fall back to stub
            logger.warning("LLM unavailable, falling back to stub")
            out = stub_response(req)
            out["debug"]["fallback"] = True

    # Contract validation (hard gate)
    try:
        validate(instance=out, schema=SCHEMA)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contract validation failed: {e}")

    return out


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
