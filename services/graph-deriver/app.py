#!/usr/bin/env python3
"""
graph-deriver service: Deterministic graph extraction from events
Runs as daemon, polls for new events, creates nodes/edges with evidence links
"""
import os
import sys
import time
import hashlib
import logging
from typing import Any, Optional

import psycopg2
import psycopg2.extras

# Environment
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "continuuai")
DB_USER = os.getenv("DB_USER", "continuuai")
DB_PASS = os.getenv("DB_PASS", "dev_password")
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "10"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("graph-deriver")


def stable_hash(org_id: str, text: str) -> str:
    """Generate stable node key from org + text"""
    return hashlib.sha256(f"{org_id}:{text}".encode("utf-8")).hexdigest()[:24]


class GraphDeriver:
    """Derives graph nodes/edges from event stream"""
    
    def __init__(self, conn):
        self.conn = conn
        
    def upsert_node(self, org_id: str, node_type: str, key: str, 
                    title: str, canonical_text: Optional[str] = None,
                    metadata: Optional[dict] = None) -> str:
        """Insert or update node, returns node_id (uuid)"""
        metadata = metadata or {}
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO graph_node 
                  (org_id, node_type, key, title, canonical_text, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (org_id, node_type, key) DO UPDATE SET
                  title = EXCLUDED.title,
                  canonical_text = COALESCE(EXCLUDED.canonical_text, graph_node.canonical_text),
                  metadata = graph_node.metadata || EXCLUDED.metadata,
                  updated_at = now()
                RETURNING node_id;
            """, (org_id, node_type, key, title, canonical_text, 
                  psycopg2.extras.Json(metadata)))
            node_id = cur.fetchone()[0]
            self.conn.commit()
            return str(node_id)
    
    def upsert_edge(self, org_id: str, src_node_id: str, dst_node_id: str,
                    edge_type: str, weight: float = 1.0,
                    metadata: Optional[dict] = None) -> str:
        """Insert or update edge, returns edge_id (uuid)"""
        metadata = metadata or {}
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO graph_edge
                  (org_id, src_node_id, dst_node_id, edge_type, weight, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (org_id, src_node_id, dst_node_id, edge_type) DO UPDATE SET
                  weight = EXCLUDED.weight,
                  metadata = graph_edge.metadata || EXCLUDED.metadata,
                  updated_at = now()
                RETURNING edge_id;
            """, (org_id, src_node_id, dst_node_id, edge_type, weight,
                  psycopg2.extras.Json(metadata)))
            edge_id = cur.fetchone()[0]
            self.conn.commit()
            return str(edge_id)
    
    def attach_edge_evidence(self, edge_id: str, event_id: str):
        """Link edge to evidence spans from source event and populate span_node."""
        with self.conn.cursor() as cur:
            # 1) Attach edge_evidence for spans from the event's artifact
            cur.execute("""
                WITH spans AS (
                  SELECT es.evidence_span_id, es.org_id
                  FROM evidence_span es
                  JOIN event_log el ON el.artifact_id = es.artifact_id
                  WHERE el.event_id = %s
                )
                INSERT INTO edge_evidence (edge_id, evidence_span_id, confidence, evidence_type, created_by)
                SELECT 
                  %s AS edge_id,
                  s.evidence_span_id,
                  0.85 AS confidence,
                  'derived_from_event' AS evidence_type,
                  'graph-deriver' AS created_by
                FROM spans s
                ON CONFLICT (edge_id, evidence_span_id) DO NOTHING;
            """, (event_id, edge_id))

            # 2) Link spans directly to both src/dst nodes via span_node (if table exists)
            cur.execute("""
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'span_node'
                  ) THEN
                    INSERT INTO span_node (org_id, evidence_span_id, node_id)
                    SELECT ge.org_id, es.evidence_span_id, ge.src_node_id
                    FROM edge_evidence ee
                    JOIN graph_edge ge ON ge.edge_id = ee.edge_id
                    JOIN evidence_span es ON es.evidence_span_id = ee.evidence_span_id
                    WHERE ee.edge_id = %s
                    ON CONFLICT (org_id, evidence_span_id, node_id) DO NOTHING;

                    INSERT INTO span_node (org_id, evidence_span_id, node_id)
                    SELECT ge.org_id, es.evidence_span_id, ge.dst_node_id
                    FROM edge_evidence ee
                    JOIN graph_edge ge ON ge.edge_id = ee.edge_id
                    JOIN evidence_span es ON es.evidence_span_id = ee.evidence_span_id
                    WHERE ee.edge_id = %s
                    ON CONFLICT (org_id, evidence_span_id, node_id) DO NOTHING;
                  END IF;
                END $$;
            """, (edge_id, edge_id))

            self.conn.commit()
    
    def derive_from_event(self, event: dict):
        """
        Main derivation logic: extract nodes/edges from event payload
        
        Event structure (from ingest):
        {
          "event_id": "uuid",
          "org_id": "uuid",
          "event_type": "ingest_completed",
          "event_ts": "timestamp",
          "actor": "email",
          "artifact_id": "uuid",
          "payload": {
            "kind": "decision|assumption|outcome|priority|...",
            "title": "text",
            "description": "text",
            "decision_ref": "optional decision key",
            "assumptions": [...],
            "priority": "P0|P1|P2",
            "owner": "person name",
            ...
          }
        }
        """
        org_id = str(event["org_id"])
        event_id = str(event["event_id"])
        actor = event.get("actor", "system")
        payload = event.get("payload", {})
        kind = payload.get("kind", "")
        
        logger.info(f"Deriving from event {event_id}, kind={kind}")
        
        # Decision nodes
        if kind == "decision":
            title = payload.get("title", "Untitled Decision")
            desc = payload.get("description", "")
            priority = payload.get("priority", "P2")
            
            # Create decision node
            decision_key = stable_hash(org_id, title)
            decision_node_id = self.upsert_node(
                org_id=org_id,
                node_type="decision",
                key=decision_key,
                title=title,
                canonical_text=desc,
                metadata={
                    "source_event_id": event_id,
                    "priority": priority,
                    "decided_by": actor
                }
            )
            
            # Create person node for owner if specified
            owner = payload.get("owner")
            if owner:
                owner_key = stable_hash(org_id, owner)
                owner_node_id = self.upsert_node(
                    org_id=org_id,
                    node_type="person",
                    key=owner_key,
                    title=owner,
                    metadata={"source_event_id": event_id}
                )
                # Link decision -> owns -> person
                edge_id = self.upsert_edge(
                    org_id=org_id,
                    src_node_id=decision_node_id,
                    dst_node_id=owner_node_id,
                    edge_type="decided_by",
                    weight=1.0,
                    metadata={"derived_from": event_id}
                )
                self.attach_edge_evidence(edge_id, event_id)
            
            # Extract assumptions
            assumptions = payload.get("assumptions", [])
            for assumption_text in assumptions:
                if not assumption_text.strip():
                    continue
                assumption_key = stable_hash(org_id, assumption_text)
                assumption_node_id = self.upsert_node(
                    org_id=org_id,
                    node_type="assumption",
                    key=assumption_key,
                    title=assumption_text[:200],
                    canonical_text=assumption_text,
                    metadata={"source_event_id": event_id}
                )
                # Link decision -> depends_on -> assumption
                edge_id = self.upsert_edge(
                    org_id=org_id,
                    src_node_id=decision_node_id,
                    dst_node_id=assumption_node_id,
                    edge_type="depends_on",
                    weight=0.9,
                    metadata={"derived_from": event_id}
                )
                self.attach_edge_evidence(edge_id, event_id)
            
            # Create priority node
            priority_key = stable_hash(org_id, f"priority_{priority}")
            priority_node_id = self.upsert_node(
                org_id=org_id,
                node_type="priority",
                key=priority_key,
                title=f"Priority {priority}",
                metadata={"level": priority}
            )
            edge_id = self.upsert_edge(
                org_id=org_id,
                src_node_id=decision_node_id,
                dst_node_id=priority_node_id,
                edge_type="relates_to",
                weight=0.8,
                metadata={"derived_from": event_id}
            )
            self.attach_edge_evidence(edge_id, event_id)
        
        # Outcome nodes
        elif kind == "outcome":
            title = payload.get("title", "Untitled Outcome")
            desc = payload.get("description", "")
            decision_ref = payload.get("decision_ref")
            
            # Create outcome node
            outcome_key = stable_hash(org_id, title)
            outcome_node_id = self.upsert_node(
                org_id=org_id,
                node_type="outcome",
                key=outcome_key,
                title=title,
                canonical_text=desc,
                metadata={"source_event_id": event_id}
            )
            
            # Link to decision if referenced
            if decision_ref:
                # Find decision node by key pattern
                with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT node_id FROM graph_node
                        WHERE org_id = %s AND node_type = 'decision' 
                          AND (key = %s OR title ILIKE %s)
                        LIMIT 1;
                    """, (org_id, decision_ref, f"%{decision_ref}%"))
                    row = cur.fetchone()
                    if row:
                        decision_node_id = str(row["node_id"])
                        edge_id = self.upsert_edge(
                            org_id=org_id,
                            src_node_id=decision_node_id,
                            dst_node_id=outcome_node_id,
                            edge_type="affects",
                            weight=1.0,
                            metadata={"derived_from": event_id}
                        )
                        self.attach_edge_evidence(edge_id, event_id)
        
        # Risk nodes
        elif kind == "risk":
            title = payload.get("title", "Untitled Risk")
            desc = payload.get("description", "")
            severity = payload.get("severity", "medium")
            
            risk_key = stable_hash(org_id, title)
            risk_node_id = self.upsert_node(
                org_id=org_id,
                node_type="risk",
                key=risk_key,
                title=title,
                canonical_text=desc,
                metadata={
                    "source_event_id": event_id,
                    "severity": severity
                }
            )
            
            # Link to related decision/project if specified
            relates_to = payload.get("relates_to")
            if relates_to:
                with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT node_id FROM graph_node
                        WHERE org_id = %s 
                          AND (key = %s OR title ILIKE %s)
                        ORDER BY created_at DESC
                        LIMIT 1;
                    """, (org_id, relates_to, f"%{relates_to}%"))
                    row = cur.fetchone()
                    if row:
                        target_node_id = str(row["node_id"])
                        edge_id = self.upsert_edge(
                            org_id=org_id,
                            src_node_id=risk_node_id,
                            dst_node_id=target_node_id,
                            edge_type="affects",
                            weight=0.9,
                            metadata={"derived_from": event_id}
                        )
                        self.attach_edge_evidence(edge_id, event_id)
        
        # Generic event node for everything else
        else:
            title = payload.get("title", f"Event {event['event_type']}")
            event_node_key = stable_hash(org_id, f"event_{event_id}")
            self.upsert_node(
                org_id=org_id,
                node_type="event",
                key=event_node_key,
                title=title,
                canonical_text=str(payload),
                metadata={
                    "event_id": event_id,
                    "event_type": event["event_type"]
                }
            )


def main():
    """Main daemon loop"""
    logger.info(f"Starting graph-deriver, polling every {POLL_INTERVAL_SEC}s")
    
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            conn.autocommit = False
            
            deriver = GraphDeriver(conn)
            
            # Get last processed event for each org
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT org_id FROM org;")
                orgs = [str(row["org_id"]) for row in cur.fetchall()]
            
            for org_id in orgs:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # Get derivation state
                    cur.execute("""
                        SELECT last_event_id FROM graph_derivation_state
                        WHERE org_id = %s;
                    """, (org_id,))
                    row = cur.fetchone()
                    last_event_id = str(row["last_event_id"]) if row else None
                    
                    # Fetch new events
                    if last_event_id:
                        cur.execute("""
                            SELECT * FROM event_log
                            WHERE org_id = %s 
                              AND occurred_at > (SELECT occurred_at FROM event_log WHERE event_id = %s)
                            ORDER BY occurred_at ASC;
                        """, (org_id, last_event_id))
                    else:
                        cur.execute("""
                            SELECT * FROM event_log
                            WHERE org_id = %s
                            ORDER BY occurred_at ASC;
                        """
                        , (org_id,))
                    
                    events = cur.fetchall()
                    
                    if not events:
                        continue
                    
                    logger.info(f"Processing {len(events)} new events for org {org_id}")
                    
                    for event in events:
                        try:
                            deriver.derive_from_event(dict(event))
                        except Exception as e:
                            logger.error(f"Failed to derive from event {event['event_id']}: {e}")
                            continue
                        
                        # Update derivation state
                        cur.execute("""
                            INSERT INTO graph_derivation_state (org_id, last_event_id, last_processed_at)
                            VALUES (%s, %s, now())
                            ON CONFLICT (org_id) DO UPDATE SET
                              last_event_id = EXCLUDED.last_event_id,
                              last_processed_at = now();
                        """, (org_id, str(event["event_id"])))
                        conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Deriver loop error: {e}")
        
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
