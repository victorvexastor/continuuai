from __future__ import annotations

import os, json
from typing import List, Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from service import RetrievalService, RetrievalConfig

app = FastAPI(title="Continuuai Retrieval", version="0.3.0")

DB = os.environ["DATABASE_URL"]
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://embedding:8080")

# Initialize retrieval service with config
bonus_map_env = os.environ.get("GRAPH_BONUS_MAP")
bonus_map: Dict[str, float] | None = None
if bonus_map_env:
    try:
        bonus_map = json.loads(bonus_map_env)
    except Exception:
        bonus_map = None

cfg = RetrievalConfig(
    seed_k=int(os.environ.get("SEED_K", "40")),
    hop_depth=int(os.environ.get("HOP_DEPTH", "2")),
    hop_fanout=int(os.environ.get("HOP_FANOUT", "80")),
    final_k=int(os.environ.get("FINAL_K", "12")),
    alpha_vec=float(os.environ.get("ALPHA_VEC", "0.55")),
    beta_bm25=float(os.environ.get("BETA_BM25", "0.25")),
    gamma_graph=float(os.environ.get("GAMMA_GRAPH", "0.15")),
    delta_recency=float(os.environ.get("DELTA_RECENCY", "0.05")),
    recency_halflife_days=float(os.environ.get("RECENCY_HALFLIFE_DAYS", "45.0")),

    use_mmr=os.environ.get("USE_MMR", "true").lower() in ("1","true","yes"),
    mmr_lambda=float(os.environ.get("MMR_LAMBDA", "0.7")),
    mmr_pool=int(os.environ.get("MMR_POOL", "100")),

    bonus_decision=float(os.environ.get("GRAPH_BONUS_DECISION", "1.2")),
    bonus_outcome=float(os.environ.get("GRAPH_BONUS_OUTCOME", "1.1")),
    bonus_assumption=float(os.environ.get("GRAPH_BONUS_ASSUMPTION", "1.05")),
    bonus_map=bonus_map,
)
retrieval_svc = RetrievalService(dsn=DB, cfg=cfg)

class RetrievalRequest(BaseModel):
    org_id: str
    principal_id: str
    mode: str = Field(..., pattern="^(recall|reflection|projection)$")
    query_text: str
    scopes: List[str] = []

class EvidenceSpan(BaseModel):
    id: str
    artifact_id: str
    text: str
    confidence: float
    start_char: int
    end_char: int

class RetrievalResponse(BaseModel):
    org_id: str
    query: str
    top_k: int
    results: List[dict]
    debug: dict


async def get_query_embedding(query_text: str) -> List[float] | None:
    """Get embedding for query text from embedding service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{EMBEDDING_URL}/v1/embed",
                json={"texts": [query_text]}
            )
            if response.status_code == 200:
                data = response.json()
                return data["embeddings"][0]
            else:
                return None
    except Exception as e:
        print(f"Embedding service error: {e}")
        return None


@app.get("/v1/health")
async def health():
    return {"ok": True}

@app.get("/v1/debug/weights")
async def debug_weights():
    return {
        "seed_k": cfg.seed_k,
        "hop_depth": cfg.hop_depth,
        "hop_fanout": cfg.hop_fanout,
        "final_k": cfg.final_k,
        "alpha_vec": cfg.alpha_vec,
        "beta_bm25": cfg.beta_bm25,
        "gamma_graph": cfg.gamma_graph,
        "delta_recency": cfg.delta_recency,
        "recency_halflife_days": cfg.recency_halflife_days,
        "use_mmr": cfg.use_mmr,
        "mmr_lambda": cfg.mmr_lambda,
        "mmr_pool": cfg.mmr_pool,
        "graph_bonus_map": cfg.bonus_map or {
            "decision": cfg.bonus_decision,
            "outcome": cfg.bonus_outcome,
            "assumption": cfg.bonus_assumption,
        }
    }

@app.post("/v1/retrieve", response_model=RetrievalResponse)
async def retrieve(req: RetrievalRequest) -> RetrievalResponse:
    """
    Graph-neighborhood retrieval:
    1. Seed spans (vector + lexical)
    2. Map spans → nodes via edge_evidence
    3. Expand k-hop neighborhood
    4. Collect candidate spans from expanded nodes
    5. Hybrid scoring (vector + graph + recency)
    6. Policy filter
    7. Return top-k
    """
    
    # Get query embedding for semantic search
    query_embedding = await get_query_embedding(req.query_text)
    
    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to get query embedding")
    
    # Use the graph-neighborhood retrieval service
    result = retrieval_svc.retrieve(
        org_id=req.org_id,
        query_text=req.query_text,
        query_embedding=query_embedding,
        user_id=req.principal_id,
        acl_groups=req.scopes
    )
    
    return RetrievalResponse(**result)
