-- Migration 0007: span_node mapping table
-- Directly links evidence spans to graph nodes for faster neighborhood expansion

CREATE TABLE IF NOT EXISTS span_node (
  span_node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  evidence_span_id uuid NOT NULL REFERENCES evidence_span(evidence_span_id) ON DELETE CASCADE,
  node_id uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, evidence_span_id, node_id)
);

CREATE INDEX IF NOT EXISTS idx_span_node_org_node ON span_node(org_id, node_id);
CREATE INDEX IF NOT EXISTS idx_span_node_org_span ON span_node(org_id, evidence_span_id);
