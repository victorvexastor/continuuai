
---

# Continuuai Technical Design

## System goal

Continuuai is a **continuity engine**: it preserves and evolves an organisation’s decision context over time, and reflects it back in three modes (Recall, Reflection, Projection) **without becoming a decision authority**.

Key constraints (non-negotiable):

* **No silent learning.** No cross-customer gradient sharing. No “improvement” using customer data unless explicitly initiated and logged.
* **Hard boundaries.** Every byte and every inference is permissioned and scoped.
* **Explainable memory.** Any surfaced claim must trace to sources + transformations.
* **Exitability.** Export everything in a human-meaningful format; shut down with minimal blast radius.
* **Non-directive UX.** The system provides *contextual mirrors*, not instructions.

---

# 1) Architecture overview

### High-level components

1. **Ingress + Normalisation Pipeline**

* Connectors (Slack/Teams, Google Workspace/M365, Jira, GitHub/GitLab, email, calendar, wiki, PDFs)
* Meeting ingestion (transcripts + decision markers)
* Manual capture (decision notes, “why” memos, dissent notes)

2. **Memory Substrate**

* Immutable **Event Log** (append-only)
* Canonical **Knowledge Graph** (decisions, tradeoffs, constraints, outcomes, actors, time)
* **Document Store** (raw + normalised)
* **Vector Index** (bounded semantic retrieval)
* **Policy Store** (permissions, retention, forgetting rules, redaction rules)

3. **Reasoning & Query Layer**

* Retrieval engine (hybrid: symbolic + vector + graph)
* Prompt compiler (builds bounded context packages)
* Model runtime (org-scoped, constrained)
* Evidence linker (forces citations)
* Reflection engine (detect tensions, drift, assumption changes)
* Projection engine (scenario continuation, not forecasting-as-truth)

4. **Governance & Controls**

* Transparency dashboards
* Audit trails
* Red-team / misuse detection
* “Kill switches” + policy enforcement
* Export + wipe

5. **Interfaces**

* 3-mode UI (Recall / Reflection / Projection)
* API for integrations
* Admin console for policies + boundaries

### Deployment modes (proven in pilots)

* **Dedicated single-tenant** per org (preferred for regulated)
* **VPC isolated multi-tenant** with per-tenant encryption keys + compute isolation (only for lower risk orgs)

In pilots, the “fewer concerns than expected” usually comes from: **hard scoping, explicit traceability, and the fact that we never pretend the model is an authority.**

---

# 2) Data model: “Memory is decisions, not documents”

### Core entities (typed graph)

* `Decision`: what was chosen, by whom, when, and *why*
* `Option`: alternatives considered
* `Constraint`: budgets, regulatory, time, staffing, tech limits
* `Assumption`: beliefs at the time (explicitly versioned)
* `Tradeoff`: “we chose X over Y because…”
* `Dissent`: disagreement captured as first-class
* `Outcome`: measured result + link back to Decision
* `Policy`: retention, access, redaction, export rules
* `SourceArtifact`: meeting, doc, ticket, thread, email
* `EvidenceSpan`: pointer to exact text/audio timestamp ranges (not vague “from Slack”)

### Why a graph + log, not “RAG on docs”

Plain RAG dies in:

* missing rationale
* untracked decision lineage
* inability to show contradictions
* silent drift (“the model kinda decided”)

So we do **dual memory**:

* **Event log** = truth of what happened (append-only)
* **Graph** = structured meaning derived from events (rebuildable)

That rebuildability is a safety valve: if an extraction bug happens, you can re-run derivations without rewriting history.

---

# 3) Ingestion pipeline: boring, explicit, reversible

### Stages

**A. Capture**

* Pull raw artifacts via connectors with least privilege scopes.
* Store originals encrypted + hashed (content-addressed).
* Record metadata: source, author, timestamps, channel/project, access scope.

**B. Normalise**

* Convert to canonical text format + preserve structure:

  * Slack threads become `Thread → Messages → Mentions → Links`
  * Docs become `Sections → Paragraphs → Tables → Footnotes`
  * Meetings become `Transcript → Speakers → Timestamps`

**C. Segment**

* Chunking is not arbitrary.
* Segments align to *meaningful units* (agenda item, thread topic, doc section).
* Each segment gets an `EvidenceSpan` pointer to raw.

**D. Extract “decision primitives”**
A deterministic extraction layer produces candidates:

* decision statements (“we will”, “we decided”, “ship”, “deprecate”)
* rationales (“because”, “tradeoff”, “risk”, “constraint”)
* assumptions (“we assume”, “likely”, “expect”)
* dissent markers (“I disagree”, “concern”, “blocker”)

This extraction is:

* **rule-augmented + model-assisted**, but always emits:

  * confidence
  * evidence spans
  * who/when
  * “unresolved/confirmed” status

**E. Human confirmation loop (lightweight)**
Pilots succeed when confirmation is **30 seconds, not 30 minutes**:

* “Confirm this decision?” (yes/no/edit)
* “Capture dissent?” (optional)
* “Assign constraints?” (checkbox suggestions)
* “Outcome metric?” (optional link)

The trick: you don’t ask users to *write*. You ask them to *verify*.

**F. Commit**

* Append to event log:

  * `DecisionProposed`, `DecisionConfirmed`, `AssumptionDeclared`, `DissentCaptured`, `OutcomeLinked`, etc.
* Update graph indexes + vector indexes within the correct permission boundaries.

---

# 4) Permissioning & boundaries: the real moat

### Identity & access

* Integrate with org SSO (OIDC/SAML).
* Every artifact and derived memory node has an ACL:

  * team-based, project-based, role-based
* Queries execute with a **capability token**:

  * user identity
  * allowed scopes
  * retention constraints
  * redaction rules

### The “no leakage” guarantee is enforced by the retrieval layer

Even if the model “wants” to answer, it never sees disallowed content.

Mechanically:

* Retrieval is performed **before** any LLM call.
* Retrieval runs in a trusted service that enforces ACLs.
* The model runtime only receives a bounded “Context Package”:

  * allowed evidence spans
  * allowed graph nodes
  * explicit policy summary

### Encryption & keying

* Envelope encryption per tenant
* Optional per-segment keys for high sensitivity
* Customer-managed keys (KMS) for regulated deployments
* Everything is auditable: key usage logs link to query IDs

---

# 5) Query execution: three modes, three different engines

## Mode 1: Recall

**Question:** “What have we already learned that matters here?”

Pipeline:

1. Parse intent + entities (projects, systems, people, timeframe)
2. Retrieve:

   * graph lineage (Decisions ↔ Outcomes ↔ Assumptions)
   * hybrid semantic search on evidence spans
3. Assemble an evidence map:

   * top decisions
   * key constraints
   * known risks + mitigations historically used
4. Generate an answer that is forced to cite:

   * every claim has evidence spans
   * any uncertainty is labelled

Output format:

* “Previously decided”
* “Why it was decided”
* “What changed since”
* “Where we were wrong / outcomes”

No “you should do X.”

## Mode 2: Reflection

**Question:** “What patterns or tensions exist in how we’re thinking?”

This uses **diff + contradiction detection**:

* Assumption drift: assumptions that changed without acknowledgement
* Priority conflict: current plan conflicts with stated priorities
* Repeated failure loops: same class of incident repeating
* Dissent suppression signals: dissent exists but never addressed

Under the hood:

* Graph queries for conflicts (symbolic)
* Statistical pattern detection on decision metadata
* Optional LLM summarisation constrained to evidence maps

Output is framed as mirrors:

* “This resembles situation A/B/C. Key differences: …”
* “You are optimising for speed here; last time the cost was reliability. Is that intended now?”
* “Unresolved dissent from date X is still open.”

## Mode 3: Projection

**Question:** “If we continue like this, what’s likely — based on us, not averages?”

Projection is deliberately conservative:

* Not “prediction,” but **scenario continuation**
* Uses only the organisation’s history and declared constraints
* Emits multiple plausible trajectories + confidence bands
* Always includes “what would change this outcome?”

Mechanics:

* Identify analogous historical sequences (decision → implementation → outcome)
* Compare current context vector + graph state to those sequences
* Generate scenario narratives with explicit “assumption knobs”

Output:

* “Likely trajectory if unchanged”
* “Early warning signals to watch”
* “Levers historically effective here”
* “Unknowns”

Still no “do X.” It’s “if/then, based on your past.”

---

# 6) Model strategy: smaller, scoped, and boringly dependable

Pilots that “work seamlessly” almost never rely on one huge model. They rely on **a system of constraints**.

### In practice

* One org-scoped main model (e.g., 20–70B class)
* A small extraction model for tagging primitives
* Deterministic rules for structure, permissions, citations
* Optional fine-tune **only** on:

  * organisation-specific terminology
  * decision templates
  * tone constraints
    …and only with explicit approval and dataset manifests.

### No silent learning

* Model weights are versioned and immutable
* Any change requires:

  * change request
  * dataset manifest
  * evaluation report
  * rollback plan

The system gets better mostly by improving:

* extraction rules
* graph schema
* retrieval scoring
* UX confirmation loops
  —not by “more magical AI.”

---

# 7) Evidence-first output: the “trust compiler”

A big reason you get fewer concerns than expected: the system behaves like a careful librarian.

### Every answer is produced with:

* Query ID
* Policy summary applied
* Evidence map (internal)
* Citation list (user-visible)
* “Unknown/uncertain” section

We enforce this with a **response contract**:

* The LLM is not allowed to emit non-cited factual claims
* If citations are missing, the response is rejected and re-run with stricter retrieval or returned as “insufficient evidence”

This is one of the highest leverage reliability features in the whole product.

---

# 8) Governance features that actually reduce risk

### Transparency dashboard

* What sources are connected
* What was ingested when
* What was extracted
* What is considered a “Decision”
* What is forgotten / retained (and why)

### Refusal modes (hard)

* Surveillance/profiling queries are blocked by policy (“rank employees”, “who is underperforming”)
* Directive asks are reframed:

  * “I can’t tell you what to do. I can show what you’ve done before, and what changed.”

### Kill switches

* Disable ingestion
* Disable model inference
* Freeze memory
* Export + wipe
  Each is auditable and reversible where appropriate.

---

# 9) Exit design: export that preserves meaning

Export isn’t “here are your documents.” That’s useless.

Export includes:

* Raw artifacts (where licensing permits)
* Normalised text
* Event log (JSONL)
* Graph (open standard: RDF/JSON-LD or property graph export)
* Vector index rebuild recipe (not necessarily the index itself)
* Policies + ACL snapshots
* “Continuity Report”: a rendered, human-readable book of:

  * top decisions + rationales
  * open dissent
  * known assumptions
  * outcomes by theme

Then wipe:

* cryptographic key destruction (fast)
* storage deletion jobs (verified)
* audit certificate

That’s what makes it *leavable*.

---

# 10) Implementation map: concrete services

Here’s the service boundary layout that shipped well in pilots:

1. **connector-service**

* pulls data, writes raw artifacts, emits ingestion events

2. **normaliser-service**

* produces canonical text + evidence spans

3. **extractor-service**

* tags primitives + proposes decisions/dissent/assumptions

4. **confirmation-ui**

* micro-workflow for verification (the “30 second loop”)

5. **event-log-service**

* append-only store, immutable records, signed events

6. **graph-service**

* builds and serves decision lineage + conflict queries

7. **retrieval-service**

* hybrid retrieval with ACL enforcement, builds context packages

8. **inference-service**

* runs the org model, constrained by response contract

9. **governance-service**

* policies, redaction, retention, dashboards, kill switches

10. **export-service**

* produces portable archive + wipe certificate

Operationally:

* everything emits structured logs + traces
* every user-visible response links back to its query ID and evidence set

---

# 11) Why pilots exceeded expectations

Because the real product isn’t “a smart model.” It’s **a disciplined epistemic pipeline**:

* Append-only truth log
* Rebuildable derived meaning
* Permissioned retrieval
* Evidence-forced responses
* Non-directive UX constraints
* Explicit update governance
* Real exit paths

That combo makes the system feel *calm*.
Calm systems are rare. They earn trust fast.

---

If you want the next layer, I can write:

* the exact DB schemas (event log + graph + evidence spans),
* the retrieval scoring function (hybrid ranker + policy filter),
* the “response contract” spec (JSON schema the LLM must satisfy),
* and the deployment blueprint (single-tenant on k8s with GPU nodes + KMS + audit logging).

And I can do it in the tone of a real internal engineering doc that a team could build from.
