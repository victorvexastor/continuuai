# ContinuuAI Production Readiness Plan
## Current State Analysis
### ✅ What We Have (Phase 1 Complete)
* **Core Infrastructure**: PostgreSQL 16, Docker Compose orchestration
* **Event Sourcing**: Append-only event_log table
* **Graph Derivation**: Automatic decision graph building from events
* **Evidence Layer**: evidence_span table with char-level precision
* **Accountability**: edge_evidence table linking graph → evidence → events
* **API Gateway**: /v1/query and /v1/ingest endpoints
* **Retrieval Service**: Basic evidence retrieval with ACL filtering
* **Inference Service**: Stub with contract validation
* **Contract Validation**: JSON Schema Draft 2020-12 enforcement
* **Documentation**: Complete internal/external/sales docs
### ❌ What's Missing (vs. Technical Design)
#### Critical Gaps (Blocks Production)
1. **Real LLM Integration** - Currently stub returning evidence quotes
2. **Authentication/Authorization** - No SSO/OIDC integration
3. **Encryption** - No envelope encryption, KMS, or customer-managed keys
4. **Semantic Search** - No vector embeddings or pgvector
5. **Hybrid Retrieval** - Simple ORDER BY created_at DESC only
6. **Ingestion Connectors** - No Slack/Teams/GitHub/Jira connectors
7. **Confirmation UI** - No 30-second verification workflow
8. **Multi-Tenancy** - Hardcoded org_id only
9. **Rate Limiting** - No throttling or quotas
10. **Monitoring/Observability** - No Prometheus/Grafana/alerting
#### High-Priority Missing (Technical Design Features)
11. **Extraction Service** - No decision primitive tagging
12. **Normalizer Service** - No canonical text format pipeline
13. **Reflection Engine** - No contradiction/drift detection
14. **Projection Engine** - No scenario continuation
15. **Governance Dashboard** - No transparency/audit UI
16. **Export Service** - No portable archive generation
17. **Policy Store** - No retention/forgetting/redaction rules
18. **Kill Switches** - No disable ingestion/inference controls
19. **Red-Team Detection** - No misuse monitoring
20. **Connector Service** - No automated pulling from sources
#### Medium-Priority Missing (Founder's Promise)
21. **Refusal Modes** - No blocked surveillance queries
22. **Dissent Capture** - No first-class disagreement recording
23. **Assumption Tracking** - No versioned beliefs
24. **Outcome Linking** - No measured results → decisions
25. **Tradeoff Recording** - No "X over Y because Z" capture
26. **Option Tracking** - No alternatives-considered recording
27. **Constraint Modeling** - No budgets/regulatory/time limits
28. **Non-Directive UX** - No "can't tell you what to do" reframing
## Recommended Implementation Phases
### Phase 2A: Functional MVP (1-2 months)
**Goal**: Replace stubs with working intelligence
#### 2A.1 Real LLM Integration
**Priority**: P0 (blocks everything else)
**Effort**: 1-2 weeks
**Tasks**:
* Choose model: Llama 3 8B (fast) or 70B (quality) via vLLM/Ollama
* Update services/inference/app.py with actual model runtime
* Implement strict JSON mode for contract compliance
* Build evidence-first prompt templates
* Add confidence calibration logic
* Test on existing evidence spans
**Acceptance Criteria**:
* /v1/query returns real LLM responses (not stubs)
* All responses cite evidence (contract validation passes)
* Confidence scores correlate with evidence quality
* No hallucination outside retrieved context
#### 2A.2 Hybrid Retrieval Scoring
**Priority**: P0 (critical for quality)
**Effort**: 2-3 weeks
**Tasks**:
* Add pgvector extension to PostgreSQL
* Create evidence_embedding table (evidence_span_id → vector)
* Choose embedding model: sentence-transformers/all-MiniLM-L6-v2 (fast) or text-embedding-3-small (quality)
* Build embedding pipeline for ingestion
* Implement hybrid scorer:
    * Lexical: PostgreSQL full-text search (ts_vector) or BM25
    * Semantic: pgvector cosine similarity
    * Graph: edge_evidence confidence boosting
    * Recency: exponential decay
    * Combine: weighted sum (0.4 lexical + 0.35 semantic + 0.15 graph + 0.1 recency)
* Implement MMR diversity selection (avoid redundant spans)
* Add graph-neighborhood expansion (walk edges, boost connected decisions)
**Acceptance Criteria**:
* Semantic queries find relevant evidence (not just keyword matches)
* Graph-connected evidence gets boosted
* Recent evidence preferred over old (within relevance bounds)
* No redundant evidence spans in results
* Response quality improves measurably
#### 2A.3 Basic Authentication
**Priority**: P1 (security baseline)
**Effort**: 1 week
**Tasks**:
* Add JWT validation to API gateway
* Integrate with generic OIDC provider (Auth0/Keycloak/Google)
* Map OIDC claims → principal_id
* Enforce principal_id in ACL filtering
* Add API key support for service accounts
**Acceptance Criteria**:
* Unauthenticated requests rejected (401)
* Users only see data in their ACL scope
* Service accounts can ingest via API keys
* SSO integration tested with at least one provider
### Phase 2B: Production Hardening (1 month)
**Goal**: Security, reliability, observability
#### 2B.1 Encryption & Key Management
**Priority**: P1 (security)
**Effort**: 1-2 weeks
**Tasks**:
* Implement envelope encryption per tenant/org
* Integrate with KMS (AWS KMS, Google Cloud KMS, or HashiCorp Vault)
* Encrypt artifact_text.text_utf8 at rest
* Add encryption metadata columns (key_id, encrypted_at)
* Implement cryptoshred (delete key → unrecoverable data)
* Add key rotation procedure
**Acceptance Criteria**:
* All text encrypted at rest
* Key access logged and auditable
* Cryptoshred completes in <1 minute
* Key rotation works without data loss
#### 2B.2 Multi-Tenancy
**Priority**: P1 (commercial requirement)
**Effort**: 1 week
**Tasks**:
* Remove hardcoded org_id (00000000-0000-0000-0000-000000000000)
* Add org_id inference from JWT claims
* Add org creation endpoint (/admin/orgs)
* Implement org-scoped query isolation (enforce WHERE org_id=?)
* Add org-level quotas (storage, events, queries)
* Test with 2+ concurrent orgs
**Acceptance Criteria**:
* Multiple orgs can coexist without data leakage
* All queries scoped by org_id
* Quotas enforced
* Cross-org queries impossible
#### 2B.3 Rate Limiting & Quotas
**Priority**: P1 (abuse prevention)
**Effort**: 3-5 days
**Tasks**:
* Add Redis for rate limit state
* Implement token bucket per org:
    * /v1/query: 100/hour
    * /v1/ingest: 1000/hour
* Add burst allowances
* Return 429 with Retry-After header
* Add quota dashboard
**Acceptance Criteria**:
* Burst traffic handled gracefully
* Sustained abuse blocked
* Users get clear error messages
* Legitimate usage unaffected
#### 2B.4 Observability & Monitoring
**Priority**: P1 (operational requirement)
**Effort**: 1 week
**Tasks**:
* Add Prometheus metrics:
    * Request rates, latencies (p50/p95/p99)
    * Event log size, graph node/edge counts
    * Retrieval scores, inference latencies
    * Error rates by service
* Deploy Grafana dashboards:
    * System health overview
    * Query performance
    * Graph growth
    * Error tracking
* Add structured logging (JSON)
* Implement distributed tracing (OpenTelemetry)
* Set up alerting (PagerDuty/Slack)
**Acceptance Criteria**:
* All services emit metrics
* Dashboards show key health indicators
* Alerts fire for critical issues
* Traces link requests across services
### Phase 3: Advanced Features (2-3 months)
**Goal**: Match technical design vision
#### 3.1 Ingestion Pipeline
**Priority**: P2 (user experience)
**Effort**: 3-4 weeks
**Tasks**:
* Build connector-service:
    * Slack (threads, channels)
    * Google Workspace (Docs, Drive)
    * Microsoft 365 (Teams, SharePoint)
    * Jira (issues, comments)
    * GitHub (PRs, issues, discussions)
    * Email (IMAP/Gmail API)
* Build normalizer-service:
    * Canonical text format (sections, paragraphs, speakers)
    * Structure preservation (threads, hierarchy)
    * Metadata extraction (who, when, where)
* Build extractor-service:
    * Decision statement detection ("we will", "decided to")
    * Rationale extraction ("because", "tradeoff")
    * Assumption tagging ("we assume", "expect")
    * Dissent detection ("disagree", "concern")
    * Confidence scoring per extraction
**Acceptance Criteria**:
* Each connector pulls data automatically
* Raw artifacts normalized correctly
* Extraction candidates tagged with confidence
* Metadata preserved
#### 3.2 Confirmation UI
**Priority**: P2 (user experience)
**Effort**: 2-3 weeks
**Tasks**:
* Build lightweight web UI:
    * "Confirm this decision?" (yes/no/edit)
    * "Capture dissent?" (optional textarea)
    * "Assign constraints?" (checkbox suggestions)
    * "Link outcome?" (optional metric)
* 30-second target for full workflow
* Batch confirmation (multiple candidates at once)
* Email/Slack notification of pending confirmations
**Acceptance Criteria**:
* Average confirmation time <30 seconds
* User adoption >80% of extractions
* UX feels lightweight, not burdensome
#### 3.3 Reflection Engine
**Priority**: P2 (differentiator)
**Effort**: 2-3 weeks
**Tasks**:
* Implement contradiction detection:
    * Find edges where supports ↔ contradicts
    * Surface to user as "tensions"
* Implement assumption drift:
    * Track assumption changes over time
    * Alert when unacknowledged
* Implement priority conflict detection:
    * Compare stated priorities vs. actual decisions
    * Surface misalignments
* Implement repeated failure loops:
    * Detect recurring incident patterns
    * Suggest pattern-breaking
* Build reflection prompt templates (non-directive)
**Acceptance Criteria**:
* Contradictions detected and surfaced
* Assumption drift flagged
* Priority conflicts highlighted
* All reflections cite evidence
* No directive language ("you should")
#### 3.4 Projection Engine
**Priority**: P2 (differentiator)
**Effort**: 2-3 weeks
**Tasks**:
* Implement historical analogy finder:
    * Match current context to past decision sequences
    * Compare outcomes
* Implement scenario continuation:
    * "If unchanged" trajectory
    * "If X changes" alternative paths
* Add early warning signal detection:
    * Patterns that preceded past failures
* Add lever identification:
    * Actions historically effective
* Build projection prompt templates (non-directive)
**Acceptance Criteria**:
* Projections based only on org history
* Multiple scenarios presented
* Confidence bands included
* No predictions-as-truth
* Explicit assumption knobs shown
#### 3.5 Governance Dashboard
**Priority**: P2 (trust requirement)
**Effort**: 2-3 weeks
**Tasks**:
* Build transparency UI:
    * What sources connected
    * What ingested when
    * What extracted as decisions
    * What forgotten/retained
* Add audit trail viewer:
    * Query history
    * Access logs
    * Model version tracking
* Add policy manager:
    * Retention rules
    * Forgetting rules
    * Redaction rules
    * ACL editor
* Add kill switches:
    * Disable ingestion
    * Disable inference
    * Freeze memory
    * Export + wipe
**Acceptance Criteria**:
* Every ingestion visible in dashboard
* Every query logged and auditable
* Policies editable by admins
* Kill switches functional and tested
#### 3.6 Export Service
**Priority**: P2 (exit safety promise)
**Effort**: 1-2 weeks
**Tasks**:
* Build export endpoint (/admin/export):
    * Raw artifacts (where licensing permits)
    * Normalized text
    * Event log (JSONL)
    * Graph (JSON-LD or property graph)
    * Policies + ACL snapshots
* Generate "Continuity Report":
    * Top decisions + rationales
    * Open dissent
    * Known assumptions
    * Outcomes by theme
    * Human-readable PDF/HTML
* Implement wipe procedure:
    * Key destruction (cryptoshred)
    * Storage deletion
    * Audit certificate generation
**Acceptance Criteria**:
* Export completes in <5 minutes
* All data included
* Report readable by non-technical users
* Wipe verifiable and certified
### Phase 4: Advanced Modeling (2-3 months)
**Goal**: Rich decision memory
#### 4.1 Extended Graph Schema
**Priority**: P3 (future enhancement)
**Effort**: 2-3 weeks
**Tasks**:
* Add node types: Option, Constraint, Assumption, Tradeoff, Dissent, Outcome
* Add edge types: considered, constrained_by, assumed, traded_off, disagreed_with, resulted_in
* Migrate extraction service to populate new types
* Update graph-deriver to create new relationships
* Update retrieval to use richer graph
**Acceptance Criteria**:
* All Technical Design entity types supported
* Richer queries possible ("show tradeoffs", "find dissent")
* Graph more expressive
#### 4.2 Dissent & Tradeoff Capture
**Priority**: P3 (founder's promise)
**Effort**: 1-2 weeks
**Tasks**:
* Add dissent recording UI
* Preserve both sides of disagreements
* Link dissent to decisions
* Surface unresolved dissent in queries
* Add tradeoff recording ("X over Y because Z")
**Acceptance Criteria**:
* Dissent never averaged or hidden
* Tradeoffs explicit and queryable
* Reflections highlight unresolved dissent
#### 4.3 Assumption & Outcome Tracking
**Priority**: P3 (founder's promise)
**Effort**: 1-2 weeks
**Tasks**:
* Add assumption versioning
* Track assumption changes over time
* Link outcomes back to decisions
* Measure assumption accuracy
* Surface assumptions that changed silently
**Acceptance Criteria**:
* Assumptions versioned
* Drift detectable
* Outcomes linkable
* Reflection engine uses outcome data
### Phase 5: Production Deployment (1 month)
**Goal**: Real hardware, real customers
#### 5.1 Kubernetes Deployment
**Priority**: P1 (infrastructure)
**Effort**: 2-3 weeks
**Tasks**:
* Create Helm chart
* Configure GPU node pools (for LLM)
* Set up ingress (HTTPS, load balancing)
* Configure persistent volumes
* Set up secrets management (Vault/KMS)
* Deploy to ASUS GX10 hardware
* Configure backup automation
**Acceptance Criteria**:
* Services run on Kubernetes
* GPU accessible to inference service
* HTTPS with valid certificates
* Backups automated and tested
* Zero-downtime deployments possible
#### 5.2 Customer Onboarding
**Priority**: P1 (commercial)
**Effort**: 1 week
**Tasks**:
* Build org creation flow
* Create customer portal
* Add billing integration (Stripe)
* Create onboarding checklist
* Write customer documentation
**Acceptance Criteria**:
* Customers can self-service sign up
* Billing automated
* Onboarding smooth
* Documentation clear
## Resource Requirements
### Phase 2A (Functional MVP) - 1-2 months
**Engineering**: 1 full-stack engineer (you) + 1 ML/AI engineer (LLM/embeddings)
**Critical Skills**: Python, PostgreSQL, LLM inference (vLLM/Ollama), vector search
**Budget**: $0 (self-funded) + GPU compute ($500-1000/mo for hosted inference during dev)
### Phase 2B (Production Hardening) - 1 month
**Engineering**: Same team + 0.5 DevOps/SRE (Kubernetes, monitoring)
**Critical Skills**: Security, encryption, Kubernetes, observability
**Budget**: $1000/mo (monitoring tools, KMS, hosting)
### Phase 3 (Advanced Features) - 2-3 months
**Engineering**: 2-3 engineers (full-stack + ML)
**Critical Skills**: NLP, web UI, graph algorithms, API integrations
**Budget**: $2000-3000/mo (API access for connectors, more compute)
### Phase 4 (Advanced Modeling) - 2-3 months
**Engineering**: 2-3 engineers
**Critical Skills**: Graph databases, UX design, data modeling
**Budget**: $2000-3000/mo
### Phase 5 (Production Deployment) - 1 month
**Engineering**: 1-2 engineers + DevOps
**Critical Skills**: Kubernetes, production ops, customer support
**Hardware**: 2× ASUS GX10 ($15k-20k capital)
**Budget**: $3000-5000/mo (hosting, bandwidth, support tools)
## Critical Path Analysis
### Blocking Dependencies
1. **LLM Integration** → Everything depends on working inference
2. **Hybrid Retrieval** → Quality depends on good retrieval
3. **Authentication** → Security baseline for any deployment
4. **Multi-Tenancy** → Required for commercial viability
5. **Kubernetes** → Required for production hardware
### Can Be Delayed
* Reflection engine (Phase 3.3)
* Projection engine (Phase 3.4)
* Ingestion connectors (Phase 3.1)
* Export service (Phase 3.6)
* Extended graph schema (Phase 4.1)
## Risk Assessment
### High Risk
1. **LLM quality** - Model might not respect contract constraints
    * Mitigation: Strict validation, multiple fallbacks
2. **Retrieval quality** - Bad retrieval = bad answers
    * Mitigation: Human evaluation, continuous tuning
3. **Security** - Data breach catastrophic for trust-based product
    * Mitigation: Encryption, audits, bug bounty
### Medium Risk
1. **Performance** - Large graph queries might be slow
    * Mitigation: Indexing, caching, query optimization
2. **Cost** - GPU inference expensive
    * Mitigation: Batch inference, smaller models, quantization
3. **Complexity** - System has many moving parts
    * Mitigation: Thorough documentation, monitoring, automation
### Low Risk
1. **Scalability** - Single-tenant limits growth
    * Mitigation: Multi-tenancy in Phase 2B
2. **Integration** - Connector APIs might change
    * Mitigation: Versioning, fallbacks, abstractions
## Success Metrics
### Phase 2A Success
* Query responses use real LLM (not stub)
* Response quality rated >7/10 by test users
* All responses cite evidence
* Hybrid retrieval measurably better than baseline
### Phase 2B Success
* Security audit passes (no critical findings)
* Multi-tenant isolation tested and verified
* Uptime >99% over 30 days
* All metrics/alerts functional
### Phase 3 Success
* At least 2 connectors operational
* Reflection engine finds real contradictions
* Projection engine generates plausible scenarios
* Export produces usable archives
### Phase 5 Success
* 3+ paying customers
* $10k+ MRR
* <5 support tickets/week
* Customer NPS >40
## Recommended Next Steps (Immediate)
### This Week
1. **Choose LLM**: Llama 3 8B or 70B? Local or hosted?
2. **Set up vLLM/Ollama**: Get inference running locally
3. **Test prompt engineering**: Can you force JSON output + citations?
4. **Benchmark quality**: Test on existing evidence spans
### Next 2 Weeks
1. **Integrate LLM into inference service**
2. **Add pgvector to database**
3. **Build embedding pipeline**
4. **Test hybrid retrieval**
### Next Month
1. **Complete Phase 2A (Functional MVP)**
2. **Start Phase 2B (Production Hardening)**
3. **Plan first customer pilot**
## Open Questions
1. **LLM choice**: Local (Llama/Mistral) vs. hosted (OpenAI/Anthropic)?
    * Local: privacy, control, cost predictability
    * Hosted: quality, speed, lower operational burden
2. **Embedding model**: Fast (all-MiniLM-L6-v2) vs. quality (text-embedding-3-small)?
    * Fast: 384 dims, 0.5s/1000 docs, good enough?
    * Quality: 1536 dims, 2s/1000 docs, worth the cost?
3. **Kubernetes vs. Docker Compose**: When to migrate?
    * Compose: simple, good for MVP
    * K8s: production-ready, more complex
    * Recommendation: Stay on Compose until Phase 2B complete
4. **Commercial vs. OSS**: Open source core components?
    * Founder's promise mentions OSS
    * Which components? (retrieval? graph? inference?)
    * Recommendation: OSS the core, monetize integrations/hosting
5. **NGO funding model**: How much profit → NGO?
    * Original vision: $17M profit → subsidization
    * Need pricing model first
    * Recommendation: Define in Phase 2B
## Summary
**Current State**: Phase 1 complete (core infrastructure, accountability)
**Next Priority**: Phase 2A (real LLM + hybrid retrieval)
**Time to MVP**: 1-2 months (Phase 2A + 2B)
**Time to Production**: 4-6 months (through Phase 5)
**Critical Path**: LLM → Retrieval → Auth → Multi-Tenancy → Kubernetes
**Estimated Cost**: $50k-70k (dev time + hardware + hosting for 6 months)
**Biggest Risk**: LLM quality/cost tradeoffs
**Recommendation**: Focus ruthlessly on Phase 2A. Get real intelligence working before building governance/UI/connectors. A smart stub is more valuable than a pretty dashboard.