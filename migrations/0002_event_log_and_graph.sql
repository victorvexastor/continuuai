-- Append-only event log (source of truth)
CREATE TABLE IF NOT EXISTS event_log (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  event_type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  ingested_at timestamptz NOT NULL DEFAULT now(),

  actor_principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE SET NULL,

  -- pointers to artifacts created by ingest (optional)
  artifact_id uuid NULL REFERENCES artifact(artifact_id) ON DELETE SET NULL,

  -- typed payload (later: enforce via protobuf / JSON schema)
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- idempotency + trace
  idempotency_key text NULL,
  trace_id text NULL,

  -- processing cursor
  processed_at timestamptz NULL,

  UNIQUE(org_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_event_org_time ON event_log(org_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_unprocessed ON event_log(org_id, processed_at) WHERE processed_at IS NULL;

-- Minimal decision graph
CREATE TABLE IF NOT EXISTS graph_node (
  node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  node_type text NOT NULL CHECK (node_type IN ('decision','topic','artifact')),
  key text NOT NULL,          -- stable-ish identifier (e.g. "decision:feature_x_flag")
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, node_type, key)
);

CREATE TABLE IF NOT EXISTS graph_edge (
  edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  src_node_id uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  dst_node_id uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  edge_type text NOT NULL CHECK (edge_type IN ('supports','contradicts','relates','evidenced_by')),
  weight double precision NOT NULL DEFAULT 1.0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, src_node_id, dst_node_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_edge_org_src ON graph_edge(org_id, src_node_id);
CREATE INDEX IF NOT EXISTS idx_edge_org_dst ON graph_edge(org_id, dst_node_id);
