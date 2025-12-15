#!/usr/bin/env python3
import os, sys, json
import httpx
import psycopg

DB = os.environ.get("DATABASE_URL", "postgres://continuuai:continuuai@localhost:5433/continuuai")
RET_URL = os.environ.get("RETRIEVAL_URL", "http://localhost:8081/v1/retrieve")
ORG = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
PRINCIPAL = os.environ.get("PRINCIPAL_ID", "d5f99e45-b729-4ac0-8101-c972acfd883b")

async def main():
    async with httpx.AsyncClient(timeout=20.0) as client:
        payload = {
            "org_id": ORG,
            "principal_id": PRINCIPAL,
            "mode": "recall",
            "query_text": "vendor selection",
            "scopes": []
        }
        r = await client.post(RET_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        spans = data.get("results", [])
        ids = [s["id"] for s in spans]
    if not ids:
        print("No results to validate", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(DB) as conn:
        q = """
        WITH given AS (
          SELECT unnest(%s::uuid[]) AS id
        )
        SELECT g.id,
               EXISTS (
                 SELECT 1 FROM span_node sn
                 JOIN evidence_span es ON es.evidence_span_id = sn.evidence_span_id
                 WHERE es.org_id = %s AND sn.evidence_span_id = g.id
               ) AS has_span_node,
               EXISTS (
                 SELECT 1 FROM edge_evidence ee
                 JOIN evidence_span es ON es.evidence_span_id = ee.evidence_span_id
                 WHERE es.org_id = %s AND ee.evidence_span_id = g.id
               ) AS has_edge_evidence
        FROM given g;
        """
        rows = conn.execute(q, (ids, ORG, ORG)).fetchall()
    bad = [str(r[0]) for r in rows if not (r[1] or r[2])]
    if bad:
        print("Invariant failed: spans without graph provenance:", bad, file=sys.stderr)
        sys.exit(2)
    print("Invariants OK (graph provenance present)")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
