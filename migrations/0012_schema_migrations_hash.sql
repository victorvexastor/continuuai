-- Migration 0012: add file hash to schema_migrations for drift detection
ALTER TABLE schema_migrations
  ADD COLUMN IF NOT EXISTS file_sha256 text;