# ContinuuAI: From Chat to Decision Continuity
## Making Julian Actually Useful
**Status**: Research Complete, Ready for Implementation
# The Problem You've Identified
The current system is "chat with documents" - users ask Julian questions and get answers. But that's backwards from your actual promise:
> "ContinuuAI preserves **decision reasoning**, not just decisions... It reflects patterns back to you so people can see when they're repeating something, contradicting themselves, or drifting from stated priorities."
Chat is passive. Chat doesn't **process** data. Users shouldn't have to "search and scramble" - the system should surface what matters **proactively**.
# What ContinuuAI Actually Promises
From your sales materials, the core value propositions are:
1. **30-second decision capture** - "verify, don't write"
2. **Preserved dissent and uncertainty** - not smoothed over
3. **Pattern detection** - contradictions, drift, repeated mistakes
4. **Context for successors** - inherit thinking, not just outcomes
5. **Evidence-anchored everything** - no assertions without sources
# Gap Analysis: Current vs. Promise
## What's Built
* ✅ Event log (append-only)
* ✅ Evidence spans with embeddings
* ✅ Graph deriver (basic: event → nodes)
* ✅ Retrieval with ACL filtering
* ✅ Query interface (recall/reflection/projection)
* ✅ Decision recording form
* ✅ LLM integration (Gemma 27B)
## What's Missing
* ❌ **Decision streams** - no way to organize decisions by project/area
* ❌ **Proactive surfacing** - system only responds, never initiates
* ❌ **Pattern detection** - no drift/contradiction analysis
* ❌ **Dissent tracking** - captured but not surfaced meaningfully
* ❌ **Decision lifecycle** - no revisit dates, outcome linking
* ❌ **Julian's learning** - no personalization to org's terminology
* ❌ **Dashboard view** - no at-a-glance "what matters now"
* ❌ **Confirmation loop** - no "was this decision correct?" flow
# The Vision: Julian as Decision Partner
Instead of "chat with your docs", Julian should be:
1. **A decision journal** - structured capture, not freeform chat
2. **A pattern mirror** - shows contradictions without judging
3. **A continuity guardian** - alerts when context is being lost
4. **A successor briefer** - generates context packages for new people
# Proposed Architecture Changes
## 1. Decision Streams (Organization Unit)
```warp-runnable-command
decision_stream
├── stream_id, org_id, name, description
├── owner_principal_id
├── status: active | archived | reviewing
└── created_at, updated_at
```
Every decision belongs to a stream (Engineering, Product, Compliance, etc.)
## 2. Rich Decision Model (Beyond Events)
```warp-runnable-command
decision
├── decision_id, stream_id, org_id
├── what_decided (text)
├── reasoning (text)
├── constraints_at_time (jsonb)
├── alternatives_considered (jsonb)
├── decided_by (principal_id)
├── decided_at (timestamp)
├── dissent[] → dissent_record table
├── uncertainty[] → uncertainty_record table
├── revisit_date (nullable)
├── outcome_id (nullable, links to outcome)
└── status: active | superseded | revisiting
```
## 3. Proactive Analysis Engine (Cron/Background)
New service: `pattern-analyzer`
* Runs daily/weekly per org
* Detects:
    * **Assumption drift**: "You said X in March, now implying Y"
    * **Decision conflicts**: "Decision A contradicts Decision B"
    * **Forgotten revisits**: "Decision from 6 months ago was marked for review"
    * **Unresolved dissent**: "Sarah's concern from Decision X never addressed"
* Produces `insight` records surfaced in dashboard
## 4. Dashboard (Not Chat-First)
New primary UI: Decision Dashboard
```warp-runnable-command
┌─────────────────────────────────────────────────────────────┐
│  ContinuuAI Dashboard                         [Record Decision] │
├─────────────────────────────────────────────────────────────┤
│  🔔 Needs Attention (3)                                       │
│  ├── Decision "API versioning" due for revisit (was Jan 15)  │
│  ├── Potential conflict: Pricing v2 vs. Enterprise discount   │
│  └── Unresolved dissent: Security concerns on Feature X       │
├─────────────────────────────────────────────────────────────┤
│  📊 Recent Decisions                                          │
│  ├── [Product] Ship Feature Y behind flag (Dec 18)           │
│  ├── [Engineering] Migrate to Postgres 16 (Dec 15)           │
│  └── [Compliance] GDPR data retention policy (Dec 10)        │
├─────────────────────────────────────────────────────────────┤
│  💬 Ask Julian                                                │
│  [What did we decide about...                              ] │
└─────────────────────────────────────────────────────────────┘
```
## 5. Julian's Learning (Org-Specific ML)
**Not** fine-tuning the base model. Instead:
* **Terminology extraction**: Build org-specific glossary from decisions
* **Entity recognition**: Learn project names, people, systems
* **Pattern templates**: "When you discuss X, you usually care about Y"
* **Retrieval tuning**: Weight recent, relevant decisions higher
Stored in: `org_vocabulary`, `org_entity`, `org_pattern` tables
# Implementation Phases
## Phase 1: Foundation (Week 1-2)
- [ ] Add `decision_stream` table and API
- [ ] Add rich `decision` table with dissent/uncertainty
- [ ] Create `/v1/decisions` CRUD endpoints
- [ ] Update user-app Record page to use streams
- [ ] Add decision detail view
## Phase 2: Dashboard (Week 2-3)
- [ ] New dashboard page as primary landing
- [ ] "Needs Attention" component (hardcoded logic first)
- [ ] Recent decisions timeline
- [ ] Stream filter/navigation
- [ ] Move query to secondary position
## Phase 3: Pattern Analysis (Week 3-4)
- [ ] `pattern-analyzer` service (Python, cron-based)
- [ ] Assumption drift detection (compare decision reasoning over time)
- [ ] Conflict detection (embedding similarity + LLM verification)
- [ ] Revisit date tracking
- [ ] `insight` table and API
- [ ] Dashboard integration
## Phase 4: Julian's Context (Week 4-5)
- [ ] Terminology extractor (runs on decision text)
- [ ] Entity recognition (people, projects, systems)
- [ ] Enhanced retrieval with org context
- [ ] "Briefing" generation for new team members
## Phase 5: Outcome Tracking (Week 5-6)
- [ ] `outcome` table linked to decisions
- [ ] "How did this turn out?" prompt after revisit_date
- [ ] Success/failure tracking (optional, non-scoring)
- [ ] Pattern correlation (decisions with X characteristic tend to...)
# UI/UX Principles (From Your Rules)
* **30-second capture**: Verify, don't write. Pre-fill from context.
* **Non-directive**: Mirror patterns, never say "you should"
* **Evidence-anchored**: Every insight cites its source
* **Boring by design**: No gamification, no engagement metrics
* **Exit-safe**: All data exportable, no lock-in
# Technical Decisions
* **No external APIs for core**: Julian runs locally (Gemma 27B)
* **Proactive via cron, not realtime**: Pattern analysis is batch
* **Graph for relationships**: Decision conflicts via graph edges
* **Embeddings for similarity**: Detect "this looks like that"
* **LLM for synthesis only**: Not for detection (deterministic rules first)
# Success Criteria
1. User can record a decision in <60 seconds
2. Dashboard shows actionable items without being asked
3. New team member can get briefing on any decision stream
4. System surfaces when decisions conflict (before user asks)
5. Dissent is never lost - always retrievable
# What Julian Should Say
**Good** (mirrors, evidence-based):
> "You've made 3 decisions about API versioning. The March decision assumed backwards compatibility was critical. The October decision didn't mention this. Is the assumption still valid?"
**Bad** (directive, judgmental):
> "You should reconsider your API versioning approach because it's inconsistent."
# Next Steps
1. Review this plan - does it match your vision?
2. Prioritize: Which phase matters most right now?
3. Start with database migrations for decision_stream + decision
4. Build dashboard shell while backend develops
