# ContinuuAI

> Organizational memory that records not just *what* was decided — but *why*.

[![Pricing](https://img.shields.io/badge/pricing-$10k%2Fmonth-0EFFAF?style=flat-square&labelColor=0A0A0A)](https://continuuai.com)

---

## What is this

Every organization hemorrhages knowledge. People leave. Context disappears. Six months later, someone re-litigates a decision nobody remembers making.

ContinuuAI is the fix. It intercepts decisions at the moment they happen, anchors them to evidence, and makes that reasoning retrievable forever.

Ask it "Why did we choose vendor X?" and it tells you — with sources, with the exact discussion that led there, with the dissenting opinions that didn't win.

---

## How it works

```
Decision made                     Decision stored
─────────────    ────────────▶    ──────────────────────────────────
  Slack/email                     Evidence graph + reasoning chain
  Meeting note                    Searchable · Traceable · Permanent
  Code commit
```

**Query modes:**
- `recall` — retrieve past decisions and their rationale
- `ingest` — capture a new decision with evidence
- `trace` — follow the evidence chain backward

---

## Architecture

```
┌──────────────────────────────────────────┐
│              API Gateway :8080           │
├──────────────┬───────────────────────────┤
│   Retrieval  │     Graph Deriver         │
│   Service    │     (reasoning chains)    │
├──────────────┼───────────────────────────┤
│  Event Log   │     Embedding Service     │
│  (immutable) │     (semantic search)     │
├──────────────┴───────────────────────────┤
│         PostgreSQL + pgvector            │
│         (13 migrations, full ACL)        │
└──────────────────────────────────────────┘
```

8 services, Docker Compose orchestrated. One command to deploy.

---

## Quick start

```bash
bash install.sh
```

Or manual:
```bash
make setup && make deploy && make verify
```

---

## API

```bash
# Recall a past decision
curl -s http://localhost:8080/v1/query \
  -H 'content-type: application/json' \
  -d '{"org_id":"...","mode":"recall","query_text":"Why did we drop vendor X?"}'

# Ingest a new decision
curl -s http://localhost:8080/v1/ingest \
  -H 'content-type: application/json' \
  -d '{"org_id":"...","decision":"We chose Go over Rust for services","rationale":"Team velocity"}'
```

---

## Status

✅ Backend complete (retrieval, graph, event log, embeddings, API gateway)  
✅ Database schema — 13 migrations with ACL + provenance  
✅ Docker Compose — 8 services  
🔧 Frontend (management dashboard + user app) — in progress  
📱 Mobile: planned
