-- Migration 0005: Extend graph to full continuity model
-- Adds more node types, edge types, and graph derivation state tracking

-- Extend node_type constraint to include full continuity model
ALTER TABLE graph_node 
  DROP CONSTRAINT IF EXISTS graph_node_node_type_check;

ALTER TABLE graph_node
  ADD CONSTRAINT graph_node_node_type_check CHECK (
    node_type IN (
      'decision', 'topic', 'artifact',  -- existing
      'assumption', 'outcome', 'priority', 'risk', 'person', 'project', 'event', 'policy', 'metric'  -- new
    )
  );

-- Extend edge_type constraint to include full relationship types
ALTER TABLE graph_edge
  DROP CONSTRAINT IF EXISTS graph_edge_edge_type_check;

ALTER TABLE graph_edge
  ADD CONSTRAINT graph_edge_edge_type_check CHECK (
    edge_type IN (
      'supports', 'contradicts', 'relates', 'evidenced_by',  -- existing
      'depends_on', 'supersedes', 'mentions', 'owns', 'decided_by', 'affects', 'mitigates', 'relates_to'  -- new
    )
  );

-- Add metadata columns to support richer graph semantics
ALTER TABLE graph_node
  ADD COLUMN IF NOT EXISTS canonical_text text,
  ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE graph_edge
  ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

-- Add index for metadata queries
CREATE INDEX IF NOT EXISTS idx_graph_node_metadata ON graph_node USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_graph_edge_metadata ON graph_edge USING gin (metadata);

-- Graph derivation state tracking table
-- Tracks what the deriver has processed for idempotent operation
CREATE TABLE IF NOT EXISTS graph_derivation_state (
  org_id uuid PRIMARY KEY REFERENCES org(org_id) ON DELETE CASCADE,
  last_event_id uuid NOT NULL,  -- Last processed event_id from event_log
  last_processed_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Index for efficient deriver polling
CREATE INDEX IF NOT EXISTS idx_derivation_state_processed ON graph_derivation_state(last_processed_at DESC);

-- Comments for documentation
COMMENT ON TABLE graph_derivation_state IS 
  'Tracks which events have been processed by graph-deriver for idempotent operation';

COMMENT ON COLUMN graph_node.canonical_text IS 
  'Longer description or full text of the node (decisions, assumptions, etc.)';

COMMENT ON COLUMN graph_node.metadata IS 
  'Flexible JSON storage for node-specific attributes (source_event_id, tags, etc.)';

COMMENT ON COLUMN graph_edge.metadata IS 
  'Flexible JSON storage for edge-specific attributes (derived_from, confidence_source, etc.)';
