from __future__ import annotations

import os
from typing import List

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="ContinuuAI Embedding Service", version="0.1.0")

# Environment
DATABASE_URL = os.environ.get("DATABASE_URL")
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MODEL_VERSION = os.environ.get("EMBEDDING_VERSION", "v1")

# Load embedding model once at startup
print(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
print(f"Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")

class EmbeddingRequest(BaseModel):
    texts: List[str]

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model_name: str
    model_version: str
    dimension: int

class GenerateEmbeddingsRequest(BaseModel):
    """Generate embeddings for all evidence spans without them."""
    org_id: str | None = None  # If None, process all orgs
    force_regenerate: bool = False  # If True, regenerate even if embeddings exist

@app.get("/healthz")
def healthz():
    return {"ok": True, "model": MODEL_NAME, "dimension": model.get_sentence_embedding_dimension()}

@app.post("/v1/embed", response_model=EmbeddingResponse)
def embed(req: EmbeddingRequest):
    """
    Generate embeddings for a list of texts.
    Used by other services for ad-hoc embedding generation.
    """
    if not req.texts:
        raise HTTPException(status_code=400, detail="No texts provided")
    
    try:
        embeddings = model.encode(req.texts, convert_to_numpy=True)
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            dimension=model.get_sentence_embedding_dimension()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/v1/generate")
def generate_embeddings(req: GenerateEmbeddingsRequest):
    """
    Background job: Generate embeddings for all evidence spans without them.
    This runs periodically or on-demand to keep embeddings up to date.
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    
    with psycopg.connect(DATABASE_URL) as conn:
        # Find evidence spans without embeddings (or all if force_regenerate)
        query = """
            SELECT es.evidence_span_id::text, es.org_id::text,
                   SUBSTRING(at.text_utf8 FROM es.start_char+1 FOR es.end_char-es.start_char) as span_text
            FROM evidence_span es
            JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id
            LEFT JOIN evidence_embedding ee ON es.evidence_span_id = ee.evidence_span_id
                AND ee.model_name = %s
                AND ee.model_version = %s
            WHERE (ee.evidence_embedding_id IS NULL OR %s = TRUE)
        """
        
        params = [MODEL_NAME, MODEL_VERSION, req.force_regenerate]
        
        if req.org_id:
            query += " AND es.org_id = %s"
            params.append(req.org_id)
        
        query += " LIMIT 1000"  # Process in batches
        
        rows = conn.execute(query, params).fetchall()
        
        if not rows:
            return {"ok": True, "processed": 0, "message": "No evidence spans need embeddings"}
        
        # Extract span IDs and texts
        span_ids = [row[0] for row in rows]
        span_texts = [row[2] for row in rows]
        
        # Generate embeddings in batch
        embeddings = model.encode(span_texts, convert_to_numpy=True, show_progress_bar=False)
        
        # Insert embeddings
        inserted = 0
        for span_id, embedding in zip(span_ids, embeddings):
            # Convert numpy array to list for pgvector
            embedding_list = embedding.tolist()
            
            conn.execute(
                """
                INSERT INTO evidence_embedding(evidence_span_id, embedding, model_name, model_version)
                VALUES (%s::uuid, %s::vector, %s, %s)
                ON CONFLICT (evidence_span_id, model_name, model_version)
                DO UPDATE SET embedding = EXCLUDED.embedding, created_at = now()
                """,
                (span_id, embedding_list, MODEL_NAME, MODEL_VERSION)
            )
            inserted += 1
        
        conn.commit()
        
        return {
            "ok": True,
            "processed": inserted,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "message": f"Generated {inserted} embeddings"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
