-- Migration 0008: Create evidence_span if missing (idempotent)

-- Artifacts tables are expected to exist from 0001_init.sql
-- This migration is safe: it will no-op if evidence_span already exists

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'evidence_span'
  ) THEN
    CREATE TABLE evidence_span (
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

    CREATE INDEX idx_evidence_org_created ON evidence_span(org_id, created_at DESC);
  END IF;
END $$;
