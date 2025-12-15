#!/usr/bin/env python3
import json, sys, os, time
import httpx

RETRIEVAL_URL = os.environ.get("RETRIEVAL_URL", "http://localhost:8081/v1/retrieve")
ORG = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
PRINCIPAL = os.environ.get("PRINCIPAL_ID", "d5f99e45-b729-4ac0-8101-c972acfd883b")

QUERIES = [
    "vendor selection",
    "decision migrate kubernetes",
    "retention policy",
    "adopt graphrag"
]

async def run():
    async with httpx.AsyncClient(timeout=20.0) as client:
        for q in QUERIES:
            payload = {
                "org_id": ORG,
                "principal_id": PRINCIPAL,
                "mode": "recall",
                "query_text": q,
                "scopes": []
            }
            r = await client.post(RETRIEVAL_URL, json=payload)
            try:
                data = r.json()
            except Exception:
                print(f"ERR {q}: status={r.status_code} body={r.text[:200]}")
                continue
            debug = data.get("debug", {})
            print(f"q='{q}' => returned={debug.get('returned')} seed={debug.get('seed_spans')} nodes={debug.get('seed_nodes')} expand={debug.get('expanded_nodes_count')} allowed={debug.get('allowed_spans_count')} mmr={debug.get('mmr')}")
            # print first snippet
            res = data.get("results", [])
            if res:
                t = res[0].get("text", "")
                print("  top:", (t[:120] + '...') if len(t) > 120 else t)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
