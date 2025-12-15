# Changelog

All notable changes to ContinuuAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2025-12-15

### Added
- **Complete Test Suite** - 6 test suites covering integrity, security, and quality
  - Provenance invariants enforcement
  - ACL negative tests (zero-trust validation)
  - MMR property tests (diversity/deduplication)
  - Phrase query validation
  - Recency decay validation
  - Synthetic retrieval smoke test
- **Observability Infrastructure**
  - `/v1/debug/sql` endpoint for SQL template inspection (token-gated)
  - `/v1/debug/weights` endpoint for config inspection
  - `/v1/health` endpoint for health checks
  - Smoke test script for full-stack validation
  - Master test runner for all suites
- **CI/CD Pipeline** - Greenfield reproducibility CI with 11 steps
  - Fresh Postgres + Qdrant bootstrap
  - Migration hash verification (drift detection)
  - Service health validation
  - All test suites integrated
- **Comprehensive Documentation**
  - Diátaxis-based structure (tutorials, how-to, reference, explanation)
  - Complete test suite documentation
  - Operations manual and runbooks
  - Changelog tracking

### Changed
- **Documentation Structure** - Reorganized into industry-standard layout
  - Moved docs to structured directories
  - Created master documentation index
  - Archived historical planning docs
- **Retrieval Service** - Enhanced with observability endpoints
- **Test Infrastructure** - Expanded from 4 to 6 test suites

### Security
- SQL debug endpoint gated by `ADMIN_DEBUG_TOKEN`
- ACL negative tests prove zero-trust enforcement
- Migration hash verification prevents silent drift

### Performance
- Phrase query validation ensures optimal lexical search
- Recency decay tests validate temporal scoring
- MMR property tests lock diversity guarantees

---

## [0.9.0] - Previous

### Added
- **Accountability Layer Complete**
  - `edge_evidence` table linking graph edges to evidence spans
  - `span_node` table mapping spans to graph nodes
  - Complete provenance chain for all results
- **Graph Derivation Service**
  - Async event processor
  - Deterministic graph extraction
  - Edge evidence linking
- **Hybrid Retrieval**
  - Vector + lexical (BM25) + graph scoring
  - MMR diversity selection
  - Recency decay weighting
  - ACL enforcement at query time

### Changed
- **Database Schema** - Extended for accountability
  - Added pgvector extension
  - Created evidence_span table
  - Created graph_node and graph_edge tables
- **Retrieval Logic** - Graph-neighborhood expansion

---

## [0.8.0] - Initial Release

### Added
- **Core Services**
  - API Gateway (FastAPI)
  - Retrieval Service
  - Inference Service (contract-validated stub)
  - Graph Deriver
- **Database Schema**
  - Event sourcing (event_log)
  - Multi-tenancy (org, principal, role)
  - ACL model (role_scope)
  - Artifact storage
- **Response Contract** - JSON Schema validation
- **Docker Compose** - Local development stack
- **Initial Documentation** - Vision, technical design, getting started

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-12-15 | Test suite + observability complete |
| 0.9.0 | Previous | Accountability layer complete |
| 0.8.0 | Initial | Core services operational |

---

## Unreleased

### Planned for v1.1.0
- Metrics endpoint (`/v1/metrics`) in Prometheus format
- Query explain endpoint (`/v1/debug/explain`)
- OpenTelemetry tracing integration
- Performance budgets (P95 latency alerts)

### Planned for v1.2.0
- k6 load testing scripts
- Chaos testing suite
- A/B test framework for ranking
- Snapshot tests for ranking stability

### Planned for v2.0.0
- LLM integration (replace inference stub)
- Kubernetes deployment (Helm charts)
- Multi-region support
- Community governance model

---

## Breaking Changes

### v1.0.0
- None (additive changes only)

### v0.9.0
- Database schema changes (migrations 0005-0009)
- Retrieval API response format (added debug field)

### v0.8.0
- Initial release (no breaking changes)

---

## Deprecations

### Planned for v1.1.0
- Legacy retrieval mode (simple ORDER BY created_at) - use hybrid retrieval

---

## Contributors

See [CONTRIBUTORS.md](../development/CONTRIBUTORS.md) for full list.

---

## Support

- **Issues**: Report bugs at [GitHub Issues](https://github.com/yourorg/continuuai/issues)
- **Security**: security@continuuai.com
- **Commercial**: sales@continuuai.com

---

**Maintained by**: ContinuuAI Team  
**Last Updated**: 2025-12-15
