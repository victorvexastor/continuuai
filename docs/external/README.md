# ContinuuAI External Documentation

User-facing documentation for ContinuuAI - the evidence-first organizational memory system.

## For New Users

Start here:

1. **[Getting Started Guide](GETTING_STARTED.md)** - Quick setup and first queries
2. **[Vision & Philosophy](CONTINUUAI_VISION.md)** - Why ContinuuAI exists and what makes it different

## For Developers

Integration and API usage:

3. **[API Reference](API_REFERENCE.md)** - Complete endpoint documentation with examples
4. **Python/JavaScript SDKs** - See API Reference for code snippets

## What is ContinuuAI?

ContinuuAI is an **evidence-first decision intelligence system** that helps organizations:

- **Remember** past decisions with full context
- **Query** institutional knowledge naturally ("What did we decide about X?")
- **Trust** responses anchored in real evidence, not LLM hallucinations
- **Control** access with fine-grained ACLs
- **Track** how decisions connect over time via knowledge graphs

### Key Differentiators

Unlike traditional document search or pure LLM systems:

✅ **Evidence-First**: Every answer includes exact quotes with confidence scores  
✅ **Contract-Enforced**: Responses validated against strict JSON Schema  
✅ **Privacy-Respecting**: ACL filtering at database layer  
✅ **Graph-Augmented**: Understands relationships between decisions  
✅ **Event-Sourced**: Complete audit trail of all changes  

### Three Query Modes

- **Recall**: "What did we decide?" (recent, exact matches)
- **Reflection**: "What patterns exist?" (graph-weighted themes)
- **Projection**: "What should we do?" (outcome-oriented)

## Use Cases

### Engineering Teams
- Design decision records
- Post-incident learnings
- Architecture evolution tracking

### Product Teams
- Feature rationale documentation
- User research synthesis
- Roadmap decision history

### Executive Teams
- Strategic planning context
- Board meeting summaries
- Stakeholder alignment tracking

### Research Organizations
- Literature review synthesis
- Experimental decision logs
- Hypothesis tracking

## Quick Example

**Query:**
```bash
curl -X POST http://localhost:8080/v1/query \
  -H 'Content-Type: application/json' \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "principal_id": "user123",
    "mode": "recall",
    "query_text": "Why did we choose PostgreSQL over MongoDB?"
  }'
```

**Response:**
```json
{
  "answer": "PostgreSQL was chosen for ACID guarantees and mature JSON support...",
  "evidence": [
    {
      "quote": "Decision: Use PostgreSQL for transactional integrity and native JSONB indexing",
      "confidence": 0.92
    }
  ],
  "policy": {
    "status": "ok"
  }
}
```

## System Requirements

- **Local Development**: Docker 24+, Docker Compose 2.20+
- **Production**: Kubernetes 1.28+ (Helm charts provided)
- **Database**: PostgreSQL 16+

## Pricing

**Current Version (v0.1.0)**: Free and open-source

**Future Plans**:
- Self-hosted: Always free
- Cloud: Free tier (100 queries/day) + Pro tier (coming soon)
- Enterprise: On-premise with support (contact sales)

## Support

- 📖 **Documentation**: You're reading it
- 🐛 **Bug Reports**: GitHub Issues
- 💬 **Community**: Discord (link TBD)
- 🔐 **Security**: security@continuuai.org
- 💼 **Enterprise**: sales@continuuai.org

## License

Apache 2.0 (see LICENSE file)

## Roadmap

- **v0.1.0** (Current): Core evidence-first retrieval
- **v0.2.0** (Q2 2025): Authentication, webhooks, pagination
- **v0.3.0** (Q3 2025): Semantic search, hybrid scoring
- **v0.4.0** (Q4 2025): Real LLM integration (OpenAI, Anthropic, local models)
- **v1.0.0** (2026): Production-ready multi-tenant

## Contributing

Contributions welcome! See CONTRIBUTING.md (coming soon)

## Philosophy

ContinuuAI is built on three principles:

1. **Evidence Over Confidence** - Cite sources, don't guess
2. **Privacy by Default** - Access control at data layer
3. **Humility in Inference** - "I don't know" is a valid answer

Inspired by library reading rooms: quiet spaces where information is accessible, verifiable, and trustworthy.

---

**Next Steps**: Read the [Getting Started Guide](GETTING_STARTED.md) →
