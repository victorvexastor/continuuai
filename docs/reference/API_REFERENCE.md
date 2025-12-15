# ContinuuAI API Reference

## Base URL

```
http://localhost:8080
```

For production deployments, replace with your actual domain.

## Authentication

**Current Version**: Demo mode with hardcoded org_id

**Future**: JWT tokens via `/v1/auth` endpoint

## Endpoints

### Health Check

```http
GET /healthz
```

**Response:**
```json
{
  "ok": true
}
```

---

### Query (Retrieve Decisions)

```http
POST /v1/query
```

Retrieve decisions and information based on your query.

**Request Body:**
```json
{
  "org_id": "string (UUID)",
  "principal_id": "string",
  "mode": "recall|reflection|projection",
  "query_text": "string (your question)",
  "scopes": ["optional", "scope", "filters"]
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `org_id` | UUID | Yes | Organization identifier |
| `principal_id` | string | Yes | User/service making the query |
| `mode` | enum | Yes | Query mode (see below) |
| `query_text` | string | Yes | Natural language question |
| `scopes` | array | No | Scope filters (e.g., team:eng, project:api) |

**Query Modes:**

- `recall` - Find past decisions (recent, exact matches prioritized)
- `reflection` - Understand patterns and themes (graph-weighted)
- `projection` - Plan future decisions (outcome-oriented)

**Response (200 OK):**
```json
{
  "contract_version": "v1",
  "mode": "recall",
  "answer": "Natural language answer based on evidence",
  "evidence": [
    {
      "evidence_span_id": "uuid",
      "artifact_id": "uuid",
      "quote": "Exact text from source",
      "confidence": 0.92
    }
  ],
  "policy": {
    "status": "ok|insufficient_evidence|policy_denied",
    "notes": ["reason1", "reason2"]
  },
  "debug": {
    "retrieval_debug": {...},
    "services": {...}
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `contract_version` | string | Schema version (always "v1") |
| `mode` | string | Echo of request mode |
| `answer` | string | Natural language response |
| `evidence[]` | array | Source quotes with metadata |
| `evidence[].confidence` | float | Relevance score (0.0-1.0) |
| `policy.status` | enum | Access control result |
| `policy.notes[]` | array | Processing notes |
| `debug` | object | Debug metadata |

**Example:**

```bash
curl -X POST http://localhost:8080/v1/query \
  -H 'Content-Type: application/json' \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "principal_id": "user123",
    "mode": "recall",
    "query_text": "What did we decide about authentication?",
    "scopes": []
  }'
```

---

### Ingest (Record Decision)

```http
POST /v1/ingest
```

Record a new decision, meeting note, or any organizational knowledge.

**Request Body:**
```json
{
  "org_id": "string (UUID)",
  "actor_external_subject": "string",
  "event_type": "string",
  "occurred_at": "ISO8601 (optional)",
  "idempotency_key": "string (optional but recommended)",
  "source_system": "string",
  "source_uri": "string",
  "content_type": "string",
  "text_utf8": "string (your content)",
  "spans": [
    {
      "start_char": 0,
      "end_char": 100,
      "section_path": "optional",
      "confidence": 0.8
    }
  ],
  "acl_name": "string",
  "payload": {...},
  "trace_id": "string (optional)"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `org_id` | UUID | Yes | - | Organization ID |
| `actor_external_subject` | string | Yes | - | User identifier |
| `event_type` | string | Yes | - | Event classification (e.g., "decision.recorded") |
| `occurred_at` | ISO8601 | No | now() | When the decision was made |
| `idempotency_key` | string | No | null | Prevents duplicates on retry |
| `source_system` | string | No | "demo" | Where this came from |
| `source_uri` | string | No | "demo://ingest" | Source identifier |
| `content_type` | string | No | "text/plain" | MIME type |
| `text_utf8` | string | Yes | - | The actual content |
| `spans` | array | No | auto | Evidence spans (auto-segments if omitted) |
| `acl_name` | string | No | "public" | Access control list |
| `payload` | object | No | {} | Structured metadata |
| `trace_id` | string | No | null | For distributed tracing |

**Response (200 OK):**
```json
{
  "ok": true,
  "event_id": "uuid",
  "artifact_id": "uuid"
}
```

**Example:**

```bash
curl -X POST http://localhost:8080/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "actor_external_subject": "user123",
    "event_type": "decision.recorded",
    "idempotency_key": "dec-2025-01-15-auth",
    "payload": {
      "topic": "security",
      "decision_key": "decision:oauth2_implementation",
      "decision_title": "Implement OAuth2 for API authentication"
    },
    "text_utf8": "Decision: Implement OAuth2 with PKCE for API authentication. Rationale: Industry standard, good library support. Timeline: 2 weeks. Risk: Learning curve for team."
  }'
```

---

## Error Responses

### 400 Bad Request
Invalid request format or missing required fields.

```json
{
  "detail": "Validation error message"
}
```

### 502 Bad Gateway
Upstream service (retrieval/inference) failed.

```json
{
  "detail": "retrieval error: connection timeout"
}
```

### 500 Internal Server Error
Contract validation failed or internal error.

```json
{
  "detail": "Contract validation failed: missing required field 'evidence'"
}
```

---

## Response Contract Schema

All responses from `/v1/query` validate against this JSON Schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["contract_version", "mode", "answer", "evidence", "policy", "debug"],
  "properties": {
    "contract_version": { "const": "v1" },
    "mode": { "enum": ["recall", "reflection", "projection"] },
    "answer": { "type": "string", "minLength": 1 },
    "evidence": {
      "type": "array",
      "maxItems": 20,
      "items": {
        "type": "object",
        "required": ["evidence_span_id", "artifact_id", "quote", "confidence"],
        "properties": {
          "evidence_span_id": { "type": "string" },
          "artifact_id": { "type": "string" },
          "quote": { "type": "string", "minLength": 1 },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    },
    "policy": {
      "type": "object",
      "required": ["status", "notes"],
      "properties": {
        "status": { "enum": ["ok", "insufficient_evidence", "policy_denied"] },
        "notes": { "type": "array", "items": { "type": "string" } }
      }
    },
    "debug": { "type": "object" }
  }
}
```

---

## Rate Limits

**Current Version**: No rate limits (local deployment)

**Future**: 
- Free tier: 100 queries/hour, 20 ingests/hour
- Pro tier: 1000 queries/hour, 200 ingests/hour
- Enterprise: Custom limits

---

## Idempotency

Use `idempotency_key` in `/v1/ingest` to safely retry requests:

- Same key + same org_id = deduplication
- Recommended format: `{event_type}-{date}-{identifier}`
- Keys are unique per org

**Example:**
```json
{
  "idempotency_key": "decision-2025-01-15-migrate-k8s",
  ...
}
```

If you retry with the same key, you'll get success but no duplicate data.

---

## Pagination

**Current Version**: Not supported (returns recent 8 evidence spans)

**Future**: Cursor-based pagination via `cursor` parameter

---

## Webhooks

**Status**: Planned for v0.2.0

Will support notifications for:
- New decisions recorded
- Graph updates
- Query patterns (e.g., "3 failed queries for same topic")

---

## SDKs

### Python

```python
import requests

class ContinuuAI:
    def __init__(self, base_url, org_id):
        self.base_url = base_url
        self.org_id = org_id
    
    def query(self, principal_id, mode, query_text, scopes=[]):
        response = requests.post(
            f"{self.base_url}/v1/query",
            json={
                "org_id": self.org_id,
                "principal_id": principal_id,
                "mode": mode,
                "query_text": query_text,
                "scopes": scopes
            }
        )
        return response.json()
    
    def ingest(self, actor, event_type, text, **kwargs):
        payload = {
            "org_id": self.org_id,
            "actor_external_subject": actor,
            "event_type": event_type,
            "text_utf8": text,
            **kwargs
        }
        response = requests.post(
            f"{self.base_url}/v1/ingest",
            json=payload
        )
        return response.json()

# Usage
client = ContinuuAI("http://localhost:8080", "00000000-0000-0000-0000-000000000000")
result = client.query("user123", "recall", "What did we decide about auth?")
print(result["answer"])
```

### JavaScript/TypeScript

```typescript
class ContinuuAI {
  constructor(private baseUrl: string, private orgId: string) {}
  
  async query(
    principalId: string,
    mode: 'recall' | 'reflection' | 'projection',
    queryText: string,
    scopes: string[] = []
  ) {
    const response = await fetch(`${this.baseUrl}/v1/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_id: this.orgId,
        principal_id: principalId,
        mode,
        query_text: queryText,
        scopes
      })
    });
    return response.json();
  }
  
  async ingest(actor: string, eventType: string, text: string, options = {}) {
    const response = await fetch(`${this.baseUrl}/v1/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_id: this.orgId,
        actor_external_subject: actor,
        event_type: eventType,
        text_utf8: text,
        ...options
      })
    });
    return response.json();
  }
}

// Usage
const client = new ContinuuAI('http://localhost:8080', '00000000-0000-0000-0000-000000000000');
const result = await client.query('user123', 'recall', 'What did we decide about auth?');
console.log(result.answer);
```

---

## Best Practices

### 1. Always Use Idempotency Keys

```json
{
  "idempotency_key": "unique-per-decision",
  ...
}
```

### 2. Include Structured Metadata

```json
{
  "payload": {
    "decision_key": "decision:feature_x",
    "topic": "engineering",
    "stakeholders": ["alice", "bob"],
    "timeline": "Q1 2025"
  }
}
```

### 3. Set Appropriate ACLs

```json
{
  "acl_name": "engineering_team",  // Not "public"
  ...
}
```

### 4. Use Scopes for Filtering

```json
{
  "scopes": ["team:eng", "project:api_v2"],
  ...
}
```

### 5. Handle Policy Denials Gracefully

```python
result = client.query(...)
if result["policy"]["status"] == "policy_denied":
    print("You don't have access to this information")
elif result["policy"]["status"] == "insufficient_evidence":
    print("No relevant decisions found")
```

---

## Changelog

### v0.1.0 (Current)
- Initial release
- `/v1/query` and `/v1/ingest` endpoints
- Evidence-first responses
- Graph derivation

### Roadmap
- v0.2.0: Authentication, webhooks, pagination
- v0.3.0: Semantic search, hybrid scoring
- v0.4.0: Real LLM integration
- v1.0.0: Production-ready multi-tenant

---

## Support

- API Issues: GitHub Issues
- Security: security@continuuai.org (see SECURITY.md)
- Community: Discord (link TBD)
