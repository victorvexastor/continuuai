# Goal
Create a transparent, understandable system where every user type knows exactly what they can do, why it matters, and how to do it from THEIR perspective.
# User Types & Their Needs
## 1. End Users (Business Decision Makers)
**Who**: Executives, managers, team leads at client companies
**Core Need**: "I need to find what my organization decided/knows without digging through Slack/email"
**Motivation**: Save time, make informed decisions, maintain continuity
### What They Need to See
* **Home Screen**: "Ask your organization" - dead simple query box
* **Mode Selector** with clear explanations:
    * Recall: "What did we decide/discuss?" (past decisions)
    * Reflection: "What patterns do we see?" (insights)
    * Projection: "What might happen if...?" (scenarios)
* **Results**: Answer + Evidence cards showing:
    * Exact quote from source
    * Confidence score ("How sure are we?")
    * When it was said
    * Who said it (if allowed by permissions)
    * Link to original source
* **History**: "Your recent questions" - see what you asked before
* **Settings**:
    * My access level ("You can see: Engineering + Sales teams")
    * Data sources ("Your org has: 1,234 decisions indexed")
    * Privacy controls ("Your queries are private")
### Transparency Elements
* Show them WHY they got this answer (which evidence)
* Show them WHAT they DON'T have access to ("3 results hidden due to permissions")
* Show them WHEN data was last updated
* Let them rate answer quality
## 2. System Administrators (Internal Team)
**Who**: Tia, Garrett, Rohan, etc. - people managing the system
**Core Need**: "I need to know if the system is healthy and manage users/permissions"
**Motivation**: Keep system running, onboard new clients, troubleshoot issues
### What They Need to See
**Dashboard Sections**:
#### A. System Health
* Service status cards (green/red)
* Database size and growth
* Query volume (requests/hour)
* Error rate
* Response time trends
#### B. User Management
* List all users (principals)
* Add new user form:
    * Email
    * Role (user/admin/service)
    * Access groups
* Edit permissions
* Deactivate users
#### C. Access Control (ACLs)
* List access groups ("Engineering", "Sales", "Executive")
* Create new group
* Assign users to groups
* View which documents each group can see
#### D. Event Log
* Searchable table:
    * When
    * Who
    * What action
    * What data
* Filter by: date, user, event type
* Export for audit
#### E. Knowledge Graph Visualizer
* See relationships between entities
* Click entity → see all related documents
* Identify knowledge gaps
#### F. Ingestion Monitor
* What sources are connected (Slack, Jira, Confluence)
* Last sync time
* Items pending approval
* Manual upload interface
### Transparency Elements
* Show them WHO has access to WHAT
* Show them HOW the AI made decisions (debug weights)
* Show them WHAT data exists (artifact count by source)
* Let them export all audit logs
## 3. AI/ML Engineers (Dev Team)
**Who**: Technical team tuning retrieval, building features
**Core Need**: "I need to understand why queries return bad results and fix them"
**Motivation**: Improve accuracy, reduce hallucinations, optimize performance
### What They Need to See
**Dev Dashboard Sections**:
#### A. Query Analysis
* Recent queries table:
    * Query text
    * Mode
    * Response time
    * Evidence count
    * User rating (if any)
* Click query → full debug view:
    * Retrieval SQL (raw query)
    * Vector search results (with scores)
    * BM25 lexical results (with scores)
    * Graph traversal path
    * Final MMR ranking
    * Inference prompt sent to LLM
    * LLM raw response
#### B. Retrieval Tuning
* Weight sliders:
    * ALPHA_VEC (vector): 0.55
    * BETA_BM25 (lexical): 0.25
    * GAMMA_GRAPH (relationships): 0.15
    * DELTA_RECENCY (time decay): 0.05
* Live test: enter query → see results with current weights
* A/B test framework: compare two weight sets
#### C. Performance Metrics
* Query latency (p50, p95, p99)
* Cache hit rate
* Database connection pool usage
* Memory usage per service
* Error logs (filterable)
#### D. Data Quality
* Embedding coverage (% artifacts with vectors)
* Orphaned entities (in graph but no source)
* Duplicate detection
* ACL integrity checks
#### E. Test Suite Dashboard
* 6 test suites status (green/red)
* Last run time
* Coverage %
* Run tests button
### Transparency Elements
* Show them EXACTLY what SQL/vector queries ran
* Show them the FULL inference prompt
* Show them token usage and costs
* Let them export query traces for analysis
