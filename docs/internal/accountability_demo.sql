-- ============================================================
-- ContinuuAI Accountability Chain Demonstration
-- ============================================================
-- This query demonstrates how every graph edge can be traced
-- back to the exact evidence spans and source events that
-- justified it. This is the "accountability screw" that turns
-- knowledge into responsible knowledge.
-- ============================================================

-- Full accountability chain: Edge → Evidence Span → Event
SELECT 
  -- Edge information
  ge.edge_id::text,
  ge.edge_type,
  gn_src.node_type as source_node_type,
  gn_src.key as source_key,
  gn_src.title as source_title,
  gn_dst.node_type as dest_node_type,
  gn_dst.key as dest_key,
  gn_dst.title as dest_title,
  ge.weight as edge_weight,
  
  -- Evidence information
  ee.evidence_type,
  ee.confidence as evidence_confidence,
  SUBSTRING(at.text_utf8 FROM es.start_char+1 FOR LEAST(200, es.end_char-es.start_char)) as evidence_text,
  es.start_char,
  es.end_char,
  
  -- Source event information
  el.event_id::text,
  el.event_type,
  el.occurred_at,
  p.display_name as actor,
  el.payload->>'decision_key' as decision_key,
  el.payload->>'topic' as topic

FROM edge_evidence ee

-- Join to get edge details
JOIN graph_edge ge ON ee.edge_id = ge.edge_id
JOIN graph_node gn_src ON ge.src_node_id = gn_src.node_id
JOIN graph_node gn_dst ON ge.dst_node_id = gn_dst.node_id

-- Join to get evidence span and text
JOIN evidence_span es ON ee.evidence_span_id = es.evidence_span_id
JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id

-- Join to get source event
JOIN artifact a ON es.artifact_id = a.artifact_id
JOIN event_log el ON a.artifact_id = el.artifact_id

-- Join to get actor details
LEFT JOIN principal p ON el.actor_principal_id = p.principal_id

WHERE ee.org_id = '00000000-0000-0000-0000-000000000000'

ORDER BY el.occurred_at DESC, ge.edge_type, ee.confidence DESC;

-- ============================================================
-- Summary statistics
-- ============================================================
\echo '\n=== Accountability Statistics ===\n'

SELECT 
  'Total Edges' as metric,
  COUNT(*) as value
FROM graph_edge

UNION ALL

SELECT 
  'Edges with Evidence' as metric,
  COUNT(DISTINCT edge_id) as value
FROM edge_evidence

UNION ALL

SELECT 
  'Total Edge Evidence Links' as metric,
  COUNT(*) as value
FROM edge_evidence

UNION ALL

SELECT 
  'Avg Evidence per Edge' as metric,
  ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT edge_id), 0), 2) as value
FROM edge_evidence;

-- ============================================================
-- Evidence breakdown by type
-- ============================================================
\echo '\n=== Evidence Type Breakdown ===\n'

SELECT 
  ge.edge_type,
  ee.evidence_type,
  COUNT(*) as count,
  ROUND(AVG(ee.confidence), 2) as avg_confidence,
  MIN(ee.confidence) as min_confidence,
  MAX(ee.confidence) as max_confidence
FROM edge_evidence ee
JOIN graph_edge ge ON ee.edge_id = ge.edge_id
GROUP BY ge.edge_type, ee.evidence_type
ORDER BY ge.edge_type, count DESC;

-- ============================================================
-- Graph structure overview
-- ============================================================
\echo '\n=== Graph Structure ===\n'

SELECT 
  node_type,
  COUNT(*) as node_count
FROM graph_node
WHERE org_id = '00000000-0000-0000-0000-000000000000'
GROUP BY node_type
ORDER BY node_count DESC;

-- ============================================================
-- Example: Trace one answer back to source
-- ============================================================
\echo '\n=== Example: Trace Decision to Sources ===\n'
\echo 'Question: What vendor did we select for contract analysis?\n'

SELECT 
  'Answer' as step,
  1 as seq,
  gn.title as content
FROM graph_node gn
WHERE gn.node_type = 'decision' 
  AND gn.key = 'vendor:selectAI'
  AND gn.org_id = '00000000-0000-0000-0000-000000000000'

UNION ALL

SELECT 
  'Evidence' as step,
  2 as seq,
  SUBSTRING(at.text_utf8 FROM es.start_char+1 FOR 150) || '...' as content
FROM graph_edge ge
JOIN edge_evidence ee ON ge.edge_id = ee.edge_id
JOIN evidence_span es ON ee.evidence_span_id = es.evidence_span_id
JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id
WHERE ge.src_node_id = (
  SELECT node_id FROM graph_node 
  WHERE node_type = 'decision' 
    AND key = 'vendor:selectAI'
    AND org_id = '00000000-0000-0000-0000-000000000000'
)
LIMIT 1

UNION ALL

SELECT 
  'Source Event' as step,
  3 as seq,
  'Event: ' || el.event_type || 
  ' | When: ' || el.occurred_at::date::text || 
  ' | Who: ' || p.display_name as content
FROM graph_edge ge
JOIN edge_evidence ee ON ge.edge_id = ee.edge_id
JOIN evidence_span es ON ee.evidence_span_id = es.evidence_span_id
JOIN artifact a ON es.artifact_id = a.artifact_id
JOIN event_log el ON a.artifact_id = el.artifact_id
LEFT JOIN principal p ON el.actor_principal_id = p.principal_id
WHERE ge.src_node_id = (
  SELECT node_id FROM graph_node 
  WHERE node_type = 'decision' 
    AND key = 'vendor:selectAI'
    AND org_id = '00000000-0000-0000-0000-000000000000'
)
LIMIT 1

ORDER BY seq;

\echo '\n=== Key Insight ===\n'
\echo 'Every claim in the graph can be traced to:\n'
\echo '  1. The specific text (evidence span) that supports it\n'
\echo '  2. The exact event (when/who) that created that evidence\n'
\echo '  3. The confidence level of the connection\n'
\echo '\nThis is what makes it a "continuity engine" not just a chatbot.\n'
