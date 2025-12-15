from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import psycopg

DB = os.environ["DATABASE_URL"]
ORG_ID = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
SLEEP_SECONDS = float(os.environ.get("SLEEP_SECONDS", "1.5"))

def upsert_node(conn, org_id: str, node_type: str, key: str, title: str) -> str:
    row = conn.execute(
        "INSERT INTO graph_node(org_id, node_type, key, title) "
        "VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (org_id, node_type, key) DO UPDATE SET title=EXCLUDED.title "
        "RETURNING node_id::text",
        (org_id, node_type, key, title),
    ).fetchone()
    return row[0]

def upsert_edge(conn, org_id: str, src: str, dst: str, edge_type: str, weight: float = 1.0) -> str:
    row = conn.execute(
        "INSERT INTO graph_edge(org_id, src_node_id, dst_node_id, edge_type, weight) "
        "VALUES (%s,%s,%s,%s,%s) "
        "ON CONFLICT (org_id, src_node_id, dst_node_id, edge_type) DO UPDATE SET weight=EXCLUDED.weight "
        "RETURNING edge_id::text",
        (org_id, src, dst, edge_type, weight),
    ).fetchone()
    return row[0]

def attach_edge_evidence(
    conn, edge_id: str, evidence_span_id: str, confidence: float, evidence_type: str
) -> None:
    """Link edge to evidence span that justifies it."""
    conn.execute(
        "INSERT INTO edge_evidence(edge_id, evidence_span_id, confidence, evidence_type) "
        "VALUES (%s::uuid,%s::uuid,%s,%s) "
        "ON CONFLICT (edge_id, evidence_span_id) DO NOTHING",
        (edge_id, evidence_span_id, confidence, evidence_type),
    )

def process_one(conn, org_id: str) -> bool:
    row = conn.execute(
        "SELECT event_id::text, event_type, occurred_at, artifact_id::text, payload "
        "FROM event_log "
        "WHERE org_id=%s AND processed_at IS NULL "
        "ORDER BY occurred_at ASC "
        "FOR UPDATE SKIP LOCKED "
        "LIMIT 1",
        (org_id,),
    ).fetchone()

    if not row:
        return False

    event_id, event_type, occurred_at, artifact_id, payload = row
    payload = payload or {}

    topic = payload.get("topic") or event_type
    decision_key = payload.get("decision_key") or f"decision:{event_type}"
    decision_title = payload.get("decision_title") or f"Decision inferred from {event_type}"

    # Retrieve evidence spans tied to this event's artifact
    # Join with artifact_text to get the actual text content
    spans = []
    if artifact_id:
        spans = conn.execute(
            "SELECT es.evidence_span_id::text, es.artifact_id::text, "
            "       SUBSTRING(at.text_utf8 FROM es.start_char+1 FOR es.end_char-es.start_char) as text, "
            "       es.start_char, es.end_char, es.confidence "
            "FROM evidence_span es "
            "JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id "
            "WHERE es.artifact_id=%s::uuid AND es.org_id=%s",
            (artifact_id, org_id),
        ).fetchall()

    decision_node = upsert_node(conn, org_id, "decision", decision_key, decision_title)
    topic_node = upsert_node(conn, org_id, "topic", f"topic:{topic}", f"Topic: {topic}")

    edge_evidence_pairs = []  # (edge_id, evidence_span_id, confidence, evidence_type)

    if artifact_id:
        art_node = upsert_node(conn, org_id, "artifact", f"artifact:{artifact_id}", f"Artifact {artifact_id[:8]}")
        evidenced_edge = upsert_edge(conn, org_id, decision_node, art_node, "evidenced_by", 1.0)
        relates_edge = upsert_edge(conn, org_id, art_node, decision_node, "relates", 0.5)

        # Attach evidence: all spans from this event support the evidenced_by edge
        for span_id, span_artifact_id, text, start, end, conf in spans:
            # High confidence for evidenced_by (the decision is directly grounded in this artifact)
            edge_evidence_pairs.append((evidenced_edge, span_id, 0.9, "decision_ref"))
            # Lower confidence for relates edge (artifact relates back to decision)
            edge_evidence_pairs.append((relates_edge, span_id, 0.5, "keyword_match"))
    else:
        # No artifact, but still create topic edges (no evidence to attach)
        pass

    topic_edge_out = upsert_edge(conn, org_id, decision_node, topic_node, "relates", 0.8)
    topic_edge_in = upsert_edge(conn, org_id, topic_node, decision_node, "relates", 0.5)

    # If we have spans and decision_key appears in span text, attach as weak evidence for topic edges
    for span_id, span_artifact_id, text, start, end, conf in spans:
        # Simple heuristic: if decision_key or topic mentioned in span, link to topic edges
        text_lower = text.lower()
        if decision_key.lower() in text_lower or topic.lower() in text_lower:
            edge_evidence_pairs.append((topic_edge_out, span_id, 0.6, "keyword_match"))
            edge_evidence_pairs.append((topic_edge_in, span_id, 0.4, "keyword_match"))

    # Attach all edge evidence
    for edge_id, span_id, confidence, evidence_type in edge_evidence_pairs:
        attach_edge_evidence(conn, edge_id, span_id, confidence, evidence_type)

    conn.execute("UPDATE event_log SET processed_at=now() WHERE event_id=%s::uuid", (event_id,))
    evidence_msg = f", attached {len(edge_evidence_pairs)} edge_evidence" if edge_evidence_pairs else ""
    print(f"processed event {event_id} -> nodes(decision={decision_node}, topic={topic_node}){evidence_msg}")
    return True

def main():
    while True:
        with psycopg.connect(DB) as conn:
            with conn.transaction():
                did = process_one(conn, ORG_ID)
        if not did:
            time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
