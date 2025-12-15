-- Migration 0003: Edge Evidence Table
-- Purpose: Link graph edges back to the evidence spans that justified them
-- This is the "accountability screw" that turns knowledge into responsible knowledge

-- Edge Evidence Junction Table
CREATE TABLE IF NOT EXISTS edge_evidence (
    edge_evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edge_id UUID NOT NULL REFERENCES graph_edge(edge_id) ON DELETE CASCADE,
    evidence_span_id UUID NOT NULL REFERENCES evidence_span(evidence_span_id) ON DELETE CASCADE,
    
    -- How strongly this span supports this edge (0.0 - 1.0)
    confidence DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Why this span was selected as evidence for this edge
    -- (e.g., "keyword_match", "decision_ref", "causal_claim", "temporal_proximity")
    evidence_type TEXT,
    
    -- Metadata about the evidence linkage
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT DEFAULT 'graph-deriver',
    
    -- Prevent duplicate evidence attachments
    UNIQUE(edge_id, evidence_span_id)
);

-- Indexes for accountability traversal
-- "For this edge, what evidence supports it?"
CREATE INDEX idx_edge_evidence_edge ON edge_evidence(edge_id);

-- "Which edges cite this span as evidence?"
CREATE INDEX idx_edge_evidence_span ON edge_evidence(evidence_span_id);

-- "Recent evidence attachments" (for audit/debugging)
CREATE INDEX idx_edge_evidence_created ON edge_evidence(created_at DESC);

-- "High-confidence evidence only"
CREATE INDEX idx_edge_evidence_confidence ON edge_evidence(confidence DESC);

-- Composite: edge + confidence (for graph scoring)
CREATE INDEX idx_edge_evidence_edge_conf ON edge_evidence(edge_id, confidence DESC);

-- Comments for future developers
COMMENT ON TABLE edge_evidence IS 'Links graph edges to the evidence spans that justify them. This enables "show your work" accountability—every claim in the graph can be traced back to source events.';
COMMENT ON COLUMN edge_evidence.confidence IS 'How strongly this span supports this edge (0.0-1.0). Used for hybrid scoring in retrieval.';
COMMENT ON COLUMN edge_evidence.evidence_type IS 'Why this span supports this edge: keyword_match, decision_ref, causal_claim, temporal_proximity, explicit_link, etc.';

-- Grant permissions (adjust based on your user setup)
-- GRANT SELECT ON edge_evidence TO continuuai_reader;
-- GRANT INSERT, UPDATE, DELETE ON edge_evidence TO continuuai_writer;
