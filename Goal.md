# Goal
Build everything needed so when GPU hardware arrives, staff run **one command** and see:
* Internal management dashboard (live)
* User-facing app (web/iOS/Android)
* Fully operational system
# Current State
## ✅ Complete (No Changes Needed)
* Backend services: retrieval, graph-deriver, event-log, api-gateway, embedding
* Database: 13 migrations, full schema with ACL/provenance
* Docker Compose: 8 services orchestrated
* Tests: 6 test suites (~19s runtime)
* Documentation: Diátaxis framework
## ❌ Missing (Blocks "One Command" Goal)
* Internal management dashboard (0%)
* User-facing web app (0%)
* iOS/Android apps (0%)
* One-command installer script (0%)
* LLM integration (stub only, needs hardware)
# Architecture Decisions
## Frontend Stack
* **Internal Dashboard**: Next.js 15 (App Router) + shadcn/ui + Recharts
* **User App (Web)**: Next.js 15 + Tailwind CSS
* **Mobile**: React Native (Expo) for iOS + Android (shared codebase)
* **Why**: Fast dev, shared components, works without GPU
## Deployment Model
* **One-command installer**: `bash install.sh` or `make deploy`
* **Under the hood**: Docker Compose (already exists) + nginx reverse proxy
* **URLs**: 
    * `http://localhost:3000` → User app
    * `http://localhost:3001` → Internal dashboard
    * `http://localhost:8080` → API Gateway
# Implementation Plan
## Phase 1: One-Command Installer (1-2 days)
**Goal**: `bash install.sh` starts entire system
### Tasks
1. Create `install.sh` (Linux/Mac detection, Docker check, port conflicts)
2. Create `Makefile` with targets: `make deploy`, `make stop`, `make logs`, `make reset`
3. Update `docker-compose.yml` to include nginx + frontend containers
4. Add `.env.example` with all configuration options
5. Create `scripts/verify_deployment.sh` (health checks all services)
6. Test on fresh Ubuntu 24.04 VM
### Success Criteria
* Fresh machine: clone repo → `bash install.sh` → all services running in <5 minutes
* Browser opens to localhost:3000 automatically
* All health checks green
## Phase 2: Internal Management Dashboard (3-5 days)
**Goal**: Staff can manage system without SQL
### Features (Priority Order)
1. **System Health** (1 day)
    * Service status (postgres, retrieval, graph-deriver, etc.)
    * Database connection pool metrics
    * Disk usage, memory, CPU
    * Recent error logs
    * Uses: `/v1/health`, `/debug/weights`, `/debug/sql` endpoints
2. **User Management** (1 day)
    * List principals (users/services/agents)
    * Create/edit/disable principals
    * View principal activity (event log)
    * ACL assignment per principal
    * CRUD on `principal` table via new API endpoints
3. **Access Control** (1 day)
    * List ACLs
    * Create/edit ACLs
    * View which artifacts use which ACLs
    * ACL grant/revoke per principal
    * CRUD on `acl`, `acl_grant` tables via new API endpoints
4. **Event Log Viewer** (1 day)
    * Paginated event list (newest first)
    * Filter by: org, principal, event_type, date range
    * View event payload (JSON)
    * Link to artifact/spans
    * Query `event_log` table via new API endpoint
5. **Knowledge Graph Visualizer** (1 day - optional for v1)
    * D3.js graph of entity relationships
    * Click entity → see artifacts
    * Query `entity`, `relationship` tables via new API endpoint
### Tech Stack
* **Framework**: Next.js 15 (App Router)
* **UI**: shadcn/ui (Tailwind-based components)
* **Charts**: Recharts
* **Auth**: Simple token-based (env var: `ADMIN_TOKEN`)
* **API**: Add `/admin/*` endpoints to api-gateway
### New API Endpoints Needed
```warp-runnable-command
POST /admin/principals (create)
GET  /admin/principals (list + filter)
PUT  /admin/principals/:id (edit)
GET  /admin/events (paginated + filter)
GET  /admin/acls (list)
POST /admin/acls (create)
POST /admin/acls/:id/grants (grant/revoke)
GET  /admin/health (system metrics)
GET  /admin/graph/entities (for visualizer)
```
### File Structure
```warp-runnable-command
services/admin-dashboard/
├── app/
│   ├── layout.tsx (shared layout)
│   ├── page.tsx (system health)
│   ├── principals/page.tsx
│   ├── acls/page.tsx
│   ├── events/page.tsx
│   └── graph/page.tsx
├── components/
│   ├── ui/ (shadcn components)
│   ├── ServiceStatus.tsx
│   ├── EventTable.tsx
│   └── PrincipalForm.tsx
├── lib/
│   ├── api.ts (fetch wrappers)
│   └── types.ts (TypeScript types)
├── Dockerfile
├── package.json
└── next.config.js
```
### Success Criteria
* Staff can view system health without SSH
* Staff can create users/ACLs via UI (no SQL)
* Event log searchable and readable
* All tables/charts render <500ms
## Phase 3: User-Facing Web App (2-3 days)
**Goal**: End users can query memory, see evidence
### Features (Priority Order)
1. **Query Interface** (1 day)
    * Text input for query
    * Mode selector (Recall/Reflection/Projection)
    * Submit button → loading state
    * Display answer + evidence quotes
    * Uses: `/v1/query` endpoint (already exists)
2. **Evidence Display** (1 day)
    * Show evidence spans with confidence scores
    * Link to source artifact (if available)
    * Highlight which span supports which part of answer
    * Copy quote to clipboard
3. **Conversation History** (1 day)
    * List past queries (stored in browser localStorage)
    * Click to reload query + answer
    * Clear history button
    * Optional: backend persistence (new `conversation` table)
### Tech Stack
* **Framework**: Next.js 15 (App Router)
* **UI**: Tailwind CSS + Radix UI primitives
* **Auth**: OAuth2/OIDC (placeholder for now, env var for principal_id)
* **API**: Uses existing `/v1/query`, `/v1/ingest`
### File Structure
```warp-runnable-command
services/user-app/
├── app/
│   ├── layout.tsx
│   ├── page.tsx (query interface)
│   ├── history/page.tsx
│   └── settings/page.tsx
├── components/
│   ├── QueryForm.tsx
│   ├── AnswerDisplay.tsx
│   ├── EvidenceCard.tsx
│   └── HistoryList.tsx
├── lib/
│   ├── api.ts
│   ├── storage.ts (localStorage wrapper)
│   └── types.ts
├── Dockerfile
├── package.json
└── next.config.js
```
### Success Criteria
* User types query → sees answer in <3 seconds (with stub LLM)
* Evidence quotes clickable and traceable
* History persists across page reloads
* Responsive (mobile-friendly)
## Phase 4: Mobile Apps (iOS + Android) (4-6 days)
**Goal**: Native apps for iOS/Android with same features as web
### Approach
* **Framework**: React Native (Expo) for shared codebase
* **Features**: Same as user-facing web app (query, history, evidence)
* **Auth**: OAuth2/OIDC (when ready)
* **Offline**: Cache last 50 queries (AsyncStorage)
### File Structure
```warp-runnable-command
services/mobile-app/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx (query)
│   │   └── history.tsx
│   └── _layout.tsx
├── components/
│   ├── QueryForm.tsx
│   ├── AnswerDisplay.tsx
│   └── EvidenceCard.tsx
├── lib/
│   ├── api.ts
│   └── storage.ts (AsyncStorage)
├── app.json (Expo config)
└── package.json
```
### Success Criteria
* iOS app builds and runs in Simulator
* Android app builds and runs in Emulator
* Query/answer flow works (uses localhost or Tailscale)
* Offline history works
## Phase 5: LLM Integration (Hardware-Dependent) (1-2 days)
**Goal**: Swap inference stub for real LLM
### When GPU Arrives
1. Add Ollama service to `docker-compose.yml` (with `--gpus all`)
2. Update `services/inference/app.py` to call Ollama API
3. Keep contract validation (already exists)
4. Test with prompt: "Based on evidence: {quotes}, answer: {query}"
5. Tune temperature, max_tokens for quality
### No Code Changes Needed Elsewhere
* API gateway already calls inference service
* Response contract already enforced
* Frontends already display answers + evidence
# Testing Strategy
## Greenfield Verification
* CI already runs 6 test suites
* Add Playwright tests for dashboards (Phase 2)
* Add Playwright tests for user app (Phase 3)
* Add Detox tests for mobile (Phase 4)
## Local Smoke Test
```warp-runnable-command
make deploy          # start everything
make verify          # run health checks
make test-ui         # run Playwright tests
make test-mobile     # run Detox tests (requires emulator)
```
# Timeline (Conservative Estimates)
| Phase | Days | Dependencies |
|-------|------|-------------|
| Phase 1: Installer | 1-2 | None |
| Phase 2: Admin Dashboard | 3-5 | Phase 1 |
| Phase 3: User Web App | 2-3 | Phase 1 |
| Phase 4: Mobile Apps | 4-6 | Phase 3 |
| Phase 5: LLM Integration | 1-2 | GPU hardware |
| **Total (No Hardware)** | **10-16 days** | |
| **Total (With Hardware)** | **11-18 days** | |
# Success Metrics
## Phase 1-4 Complete (No Hardware)
* Fresh machine: `bash install.sh` → all services + dashboards running in <5 minutes
* Staff can manage users/ACLs via UI
* Users can query (with stub LLM) and see evidence
* Mobile apps installable and functional
## Phase 5 Complete (With Hardware)
* Real LLM responses (not stub)
* Answer quality validated by humans
* All tests green
# Risk Mitigation
## Risk: Docker Compose not production-ready
* **Mitigation**: Add Kubernetes manifests (optional Phase 6)
## Risk: Frontend build times slow development
* **Mitigation**: Use Vite (faster than Webpack), hot reload
## Risk: Mobile app distribution unclear
* **Mitigation**: TestFlight (iOS), Firebase App Distribution (Android) for internal testing
# Next Steps
1. Review this plan with team
2. Start Phase 1 (installer) immediately
3. Parallel work: Phase 2 (admin) + Phase 3 (user app) can start together
4. Phase 4 (mobile) starts after Phase 3 UI components stabilized
