-- Migration 0011: Full-text search support on artifact_text
-- Adds a stored generated tsvector column and GIN index for BM25/ts_rank

ALTER TABLE artifact_text 
  ADD COLUMN IF NOT EXISTS fts_en tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(text_utf8, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_artifact_text_fts_en ON artifact_text USING GIN (fts_en);
