-- Migration 0006: Ensure pgvector extension is available
CREATE EXTENSION IF NOT EXISTS vector;