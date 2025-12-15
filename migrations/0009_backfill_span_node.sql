-- Migration 0009: Backfill span_node from edge_evidence
-- For each edge_evidence(span, edge), link span to both src and dst nodes

INSERT INTO span_node (org_id, evidence_span_id, node_id)
SELECT ge.org_id, ee.evidence_span_id, ge.src_node_id
FROM edge_evidence ee
JOIN graph_edge ge ON ge.edge_id = ee.edge_id
ON CONFLICT (org_id, evidence_span_id, node_id) DO NOTHING;

INSERT INTO span_node (org_id, evidence_span_id, node_id)
SELECT ge.org_id, ee.evidence_span_id, ge.dst_node_id
FROM edge_evidence ee
JOIN graph_edge ge ON ge.edge_id = ee.edge_id
ON CONFLICT (org_id, evidence_span_id, node_id) DO NOTHING;
