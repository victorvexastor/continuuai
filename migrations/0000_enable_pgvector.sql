-- Migration 0000: Ensure pgvector extension exists before any vector(...) columns are created
CREATE EXTENSION IF NOT EXISTS vector;