# Getting Started with ContinuuAI

## What is ContinuuAI?

ContinuuAI is an **evidence-first organizational memory system** that helps teams:

- 📝 **Track decisions** with complete context and rationale
- 🔍 **Retrieve information** with confidence scores and source citations  
- 🌐 **Build knowledge graphs** that emerge from your team's work
- 🔒 **Control access** with fine-grained permissions
- ✅ **Ensure accuracy** - every answer traces to verifiable evidence

### Why ContinuuAI?

Traditional systems have problems:
- ❌ AI answers that can't show their sources
- ❌ Lost context when people leave teams
- ❌ Decisions made without understanding past choices
- ❌ Knowledge locked in people's heads or scattered across tools

ContinuuAI solves this by making **evidence** the foundation:
- ✅ Every answer cites exact text spans with confidence scores
- ✅ Decisions automatically build a knowledge graph
- ✅ Access control happens at the data layer
- ✅ Complete audit trail of who asked what, when

## Quick Start (5 minutes)

### Prerequisites

- Docker & Docker Compose installed
- 4GB+ RAM available
- Ports 8080-8082 available

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd ContinuuAI

# Start the system
docker compose up -d

# Wait about 2 minutes for services to start
# You'll see "migrations complete" and "seed complete" in logs
```

### Verify It's Working

```bash
# Run the test suite
./test_api.sh
```

You should see: **✅ ALL TESTS PASSED!**

## Your First Query

Let's ask about decisions that were made:

```bash
curl http://localhost:8080/v1/query \
  -H 'content-type: application/json' \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "principal_id": "p1",
    "mode": "recall",
    "query_text": "What did we decide about Feature X?",
    "scopes": []
  }' | jq
```

### Response Explanation

```json
{
  "contract_version": "v1",
  "mode": "recall",
  "answer": "Based on the available evidence...",
  "evidence": [
    {
      "evidence_span_id": "...",
      "artifact_id": "...",
      "quote": "Decision confirmed: ship Feature X behind a flag.",
      "confidence": 0.92
    }
  ],
  "policy": {
    "status": "ok",
    "notes": ["evidence_anchored"]
  }
}
```

**Key parts:**
- `answer` - Natural language response
- `evidence[]` - Array of source quotes with confidence scores
- `policy.status` - Access control decision (ok/insufficient_evidence/policy_denied)
- `confidence` - 0.0 to 1.0 score for each piece of evidence

## Recording a Decision

When your team makes a decision, record it:

```bash
curl http://localhost:8080/v1/ingest \
  -H 'content-type: application/json' \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "actor_external_subject": "p1",
    "event_type": "decision.recorded",
    "idempotency_key": "my-decision-1",
    "payload": {
      "topic": "engineering",
      "decision_key": "decision:migrate_kubernetes",
      "decision_title": "Migrate to Kubernetes"
    },
    "text_utf8": "Decision: Migrate services to Kubernetes. Rationale: better scaling and resilience. Timeline: Q1 2025. Risk: team learning curve."
  }'
```

### What Happens Next

1. **Artifact Created** - Your decision text is stored
2. **Evidence Extracted** - Text is segmented into searchable spans
3. **Event Logged** - Immutable record in event log
4. **Graph Updated** - Decision, topic, and artifact nodes created automatically

Wait 2-3 seconds, then query again - your new decision will appear!

## Query Modes

ContinuuAI supports three query modes:

### 1. Recall Mode
**Use when:** Looking up past decisions

```json
{
  "mode": "recall",
  "query_text": "What did we decide about authentication?"
}
```

Returns recent evidence, prioritizing exact matches.

### 2. Reflection Mode  
**Use when:** Understanding patterns and themes

```json
{
  "mode": "reflection",
  "query_text": "What trade-offs have we made on scalability vs simplicity?"
}
```

Boosts graph connections and thematic relationships.

### 3. Projection Mode
**Use when:** Planning future decisions based on past

```json
{
  "mode": "projection",
  "query_text": "Given our past API design choices, what should we consider for the new endpoint?"
}
```

Emphasizes forward-looking evidence and outcome patterns.

## Access Control

ContinuuAI has built-in access control:

### Concepts

- **Org** - Top-level tenant (e.g., your company)
- **Principal** - A user or service account
- **ACL** - Access control list that protects artifacts
- **Role** - Groups of principals with shared permissions

### How It Works

1. Every decision/artifact has an ACL
2. ACLs grant access to specific principals or roles
3. Queries **automatically filter** to only show evidence you can access
4. No data leakage - filtering happens in the database

### Example: Team-Specific Access

```bash
# Record a decision for engineering team only
curl http://localhost:8080/v1/ingest \
  -d '{
    ...
    "acl_name": "engineering_only",
    ...
  }'

# Engineers can query it
# Non-engineers get: policy.status = "insufficient_evidence"
```

## Understanding Evidence

Every answer is built from **evidence spans**:

### Evidence Span Structure

```json
{
  "evidence_span_id": "uuid",
  "artifact_id": "uuid",
  "quote": "exact text from source",
  "confidence": 0.92,
  "start_char": 0,
  "end_char": 52,
  "section_path": "thread_id|message_id"
}
```

### What This Means

- **quote** - Exact text, not paraphrased
- **confidence** - How relevant/reliable (0.0 to 1.0)
- **start_char/end_char** - Exact position in source document
- **section_path** - Hierarchical location (e.g., document section, chat thread, meeting notes)

### Why This Matters

- ✅ **Verifiable** - You can always check the source
- ✅ **Auditable** - Track what informed each answer
- ✅ **Traceable** - Find related decisions through the graph
- ✅ **Accountable** - Know who recorded what, when

## Common Use Cases

### 1. Onboarding New Team Members

```bash
# "What architectural decisions have we made?"
# "Why did we choose PostgreSQL over MongoDB?"
# "What security policies should I know about?"
```

### 2. Sprint Planning

```bash
# "What did we learn from the last API redesign?"
# "What constraints do we have on the new feature?"
# "What trade-offs did we accept on performance?"
```

### 3. Post-Mortems

```bash
# "What decisions led to the outage?"
# "What warnings or dissent were recorded?"
# "What similar issues have we seen before?"
```

### 4. Compliance & Audits

```bash
# "Show all decisions about data retention"
# "Who approved the GDPR implementation plan?"
# "What security reviews were completed in Q3?"
```

## Next Steps

### For Users
- Read [User Guide](./USER_GUIDE.md) for detailed API reference
- See [Vision Document](./CONTINUUAI_VISION.md) for philosophy and roadmap

### For Administrators
- See [docs/internal/](../internal/) for deployment and architecture
- Review [STATUS.md](../internal/STATUS.md) for system capabilities

### For Developers
- Check [API Reference](./API_REFERENCE.md) for integration details
- See [TECHNICAL_DESIGN.md](../internal/TECHNICAL_DESIGN.md) for architecture

## Support

- Questions: Open an issue in the repository
- Security: See SECURITY.md for reporting procedures
- Roadmap: See [CONTINUUAI_VISION.md](./CONTINUUAI_VISION.md)

## Key Principles

1. **Evidence First** - Never make claims without sources
2. **Contract Validated** - Strict schemas prevent surprises
3. **Policy Respectful** - Access control baked into queries
4. **Privacy Conscious** - PII classification and retention policies
5. **Community Funded** - Profits support NGO mission

---

**You're ready!** Start recording decisions and querying your organizational memory.
