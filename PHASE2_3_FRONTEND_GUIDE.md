# Phase 2 & 3: Frontend Development Guide

**Status**: Backend ready, frontends in progress  
**Approach**: MVP first, expand incrementally

---

## 🎯 Goal

Build lightweight frontends that prove the system works end-to-end:
- **Admin Dashboard** (Phase 2): System monitoring + management
- **User App** (Phase 3): Query interface + evidence display

---

## ⚡ Fast-Track Approach (Recommended)

### Option 1: Use Existing Tools (Fastest - Hours not days)

Instead of building custom frontends immediately, use existing tools to interact with the system:

#### Admin Dashboard Alternatives
```bash
# 1. Use PostgreSQL admin tools
docker exec -it $(docker ps -qf name=postgres) psql -U continuuai -d continuuai

# 2. Use curl + jq for API testing  
curl http://localhost:8080/healthz | jq

# 3. Use make commands
make logs
make verify
make status
```

#### User App Alternatives
```bash
# Use curl to test queries
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{"org_id":"...", "mode":"recall", "query_text":"..."}'
```

**When to build custom frontends**: After backend is battle-tested with real data.

---

### Option 2: Minimal MVPs (1-2 days each)

Build bare-minimum frontends that demonstrate core functionality:

#### Admin Dashboard MVP Features
- ✅ System health check (service status)
- ✅ Database query interface (raw SQL)
- ⏳ Event log viewer (paginated table)
- ⏳ Quick actions (links to make commands)

#### User App MVP Features
- ✅ Query input box
- ✅ Display answer + evidence
- ⏳ Basic history (localStorage)

**Trade-off**: Functional but not polished. Good for demos/testing.

---

### Option 3: Full Production Frontends (10-16 days total)

Build complete, polished UIs as originally planned.

**Recommendation**: Do this **after** you've validated the backend with real usage.

---

## 🏗️ Implementation Strategy

###  Starting Point (Already Created)

I've created directory structure and starter files:

```
services/
├── admin-dashboard/
│   ├── package.json          ✅ Created
│   ├── next.config.js        ✅ Created  
│   ├── app/
│   │   ├── layout.tsx        ⏳ TODO
│   │   └── page.tsx          ✅ MVP created (health check)
│   ├── tailwind.config.js    ⏳ TODO
│   └── Dockerfile            ⏳ TODO
│
└── user-app/
    ├── package.json          ⏳ TODO
    ├── next.config.js        ⏳ TODO
    ├── app/
    │   ├── layout.tsx        ⏳ TODO
    │   └── page.tsx          ⏳ TODO (query interface)
    ├── tailwind.config.js    ⏳ TODO
    └── Dockerfile            ⏳ TODO
```

---

## 📋 Quick Setup (If Building Frontends Now)

### Admin Dashboard

```bash
cd services/admin-dashboard

# Install dependencies
npm install

# Run dev server
npm run dev

# Open http://localhost:3001
```

### User App

```bash
cd services/user-app

# Install dependencies  
npm install

# Run dev server
npm run dev

# Open http://localhost:3000
```

---

## 🚀 Recommended Next Steps

### Immediate (Today)

1. **Test Phase 1** - Verify `bash install.sh` works
2. **Load real data** - Ingest sample documents via API
3. **Test queries** - Use curl to verify retrieval works
4. **Document findings** - What works? What needs tuning?

### Short-term (This Week)

1. **Build User App MVP** - Simple query interface (1-2 days)
2. **Test with team** - Get feedback on retrieval quality
3. **Tune retrieval weights** - Adjust ALPHA/BETA/GAMMA in `.env`

### Medium-term (Next 2 Weeks)

1. **Expand User App** - Add history, better evidence display
2. **Build Admin Dashboard MVP** - Event log viewer, health monitoring
3. **Prepare for Phase 5** - When GPU hardware arrives, integrate Ollama

---

## 🛠️ Frontend Tech Stack (If Building)

### Admin Dashboard
- **Framework**: Next.js 15 (App Router)
- **UI**: Tailwind CSS + Radix UI primitives
- **Charts**: Recharts
- **API**: Fetch to `http://localhost:8080/admin/*`

### User App  
- **Framework**: Next.js 15 (App Router)
- **UI**: Tailwind CSS + Radix UI
- **State**: React hooks + localStorage
- **API**: Fetch to `http://localhost:8080/v1/*`

---

## 📦 Files Created So Far

### Admin Dashboard
- ✅ `package.json` - Dependencies defined
- ✅ `next.config.js` - Next.js configuration
- ✅ `app/page.tsx` - MVP health check page

### Remaining Files Needed

**Admin Dashboard**:
```
├── app/
│   ├── layout.tsx            # Root layout + styles
│   ├── globals.css           # Tailwind imports
│   ├── events/page.tsx       # Event log viewer
│   └── principals/page.tsx   # User management
├── lib/
│   ├── api.ts                # API client
│   └── types.ts              # TypeScript types
├── tailwind.config.js        # Tailwind configuration
├── postcss.config.js         # PostCSS config
├── tsconfig.json             # TypeScript config
└── Dockerfile                # Container build
```

**User App**: Similar structure, different pages (query, history, settings)

---

## 🧪 Testing Frontends

### Without Building Custom UIs

```bash
# 1. Test ingestion
curl -X POST http://localhost:8080/v1/ingest \
  -H "Content-Type: application/json" \
  -d @test-data.json

# 2. Test query
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d @test-query.json | jq

# 3. Check health
curl http://localhost:8080/healthz
curl http://localhost:8081/v1/health
```

### With MVPs

```bash
# Start backend
make deploy

# Start admin dashboard (separate terminal)
cd services/admin-dashboard && npm run dev

# Start user app (separate terminal)
cd services/user-app && npm run dev

# Open browsers
open http://localhost:3001  # Admin
open http://localhost:3000  # User
```

---

## 💡 My Recommendation

**Skip full frontend builds for now.** Here's why:

1. **Backend is solid** - Phase 1 complete, tested, deployed
2. **APIs work** - Can test with curl
3. **Unknown unknowns** - You don't know what features you'll need until you use it
4. **Time efficiency** - Building full UIs takes 10-16 days

**Instead**:
1. ✅ Use `make` commands and curl for now
2. ✅ Load real data and test retrieval quality
3. ✅ Wait for GPU hardware (Phase 5)
4. ✅ Build frontends **after** you've validated core functionality

**When GPU arrives**:
- `bash install.sh` → system works
- Test LLM integration
- **Then** build polished frontends with clear requirements

---

## 🎯 Decision Point

**Choose your path**:

### Path A: Build MVPs Now (2-4 days)
- Pros: Visual demonstration, easier testing
- Cons: Time investment, may need rework later

### Path B: Skip Frontends, Focus on Backend (Recommended)
- Pros: Faster to production, validate core first
- Cons: Less visual, CLI-based testing

### Path C: Hybrid Approach
- Build **only** User App MVP (1-2 days)
- Skip Admin Dashboard (use CLI tools)
- Expand later based on usage

---

**What would you like to do?**

1. Build both MVPs now (I'll continue with remaining files)
2. Build only User App MVP
3. Skip frontends, focus on testing/documentation
4. Something else?

---

**Current Status**:
- Phase 1: ✅ Complete
- GitLab: ✅ Code pushed
- Phase 2: ⚠️ Partially started (admin dashboard structure)
- Phase 3: ⏳ Not started (user app)
- Phase 5: ⏳ Waiting for GPU hardware
