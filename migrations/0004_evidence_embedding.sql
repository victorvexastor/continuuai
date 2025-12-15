-- Migration 0004: Evidence Embeddings for Semantic Search
-- Adds vector embeddings for evidence spans to enable hybrid retrieval

-- Table for storing evidence span embeddings
CREATE TABLE IF NOT EXISTS evidence_embedding (
  evidence_embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_span_id uuid NOT NULL REFERENCES evidence_span(evidence_span_id) ON DELETE CASCADE,
  
  -- Vector embedding (384 dimensions for all-MiniLM-L6-v2)
  -- Can be upgraded to 768 or 1536 for better models later
  embedding vector(384) NOT NULL,
  
  -- Embedding model metadata
  model_name text NOT NULL DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
  model_version text NOT NULL DEFAULT 'v1',
  
  -- When this embedding was generated
  created_at timestamptz NOT NULL DEFAULT now(),
  
  -- Unique constraint: one embedding per span per model version
  UNIQUE(evidence_span_id, model_name, model_version)
);

-- Index for fast vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_evidence_embedding_vector 
  ON evidence_embedding 
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Index for filtering by span before vector search
CREATE INDEX IF NOT EXISTS idx_evidence_embedding_span 
  ON evidence_embedding(evidence_span_id);

-- Index for model version tracking
CREATE INDEX IF NOT EXISTS idx_evidence_embedding_model 
  ON evidence_embedding(model_name, model_version);

-- Comments
COMMENT ON TABLE evidence_embedding IS 
  'Vector embeddings for evidence spans enabling semantic search';

COMMENT ON COLUMN evidence_embedding.embedding IS 
  'Dense vector representation of evidence span text (384-dim for MiniLM-L6-v2)';

COMMENT ON COLUMN evidence_embedding.model_name IS 
  'Name of the embedding model used (allows upgrades to better models)';
