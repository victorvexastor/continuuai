# ContinuuAI Deployment Guide

## 🚀 Quick Start

### One-Command Install (Recommended)

```bash
bash install.sh
```

This script will:
- ✅ Check system requirements (Docker, disk space, ports)
- ✅ Generate secure passwords
- ✅ Build and start all services
- ✅ Verify deployment
- ✅ Open browser to user app

**Time**: ~5 minutes on first run

---

### Manual Install (Alternative)

```bash
# 1. Setup environment
make setup

# 2. Deploy all services
make deploy

# 3. Verify health
make verify
```

---

## 📍 Access Points

Once deployed, access these URLs:

| Service | URL | Purpose |
|---------|-----|---------|
| **User App** | http://localhost:3000 | Query memory, view evidence |
| **Admin Dashboard** | http://localhost:3001 | Manage users, ACLs, view logs |
| **API Gateway** | http://localhost:8080 | REST API endpoints |
| **Database** | localhost:5433 | PostgreSQL (credentials in `.env`) |

---

## 🔧 Common Commands

```bash
# View all commands
make help

# Monitor logs
make logs                 # All services
make logs-api             # API Gateway only
make logs-db              # Database only

# Check status
make status               # Container status
make verify               # Health checks
make top                  # Resource usage

# Control services
make stop                 # Stop all
make restart              # Restart all
make clean                # Stop and remove containers (preserves data)
make reset                # ⚠️  Nuclear: delete everything and redeploy

# Database
make shell-db             # PostgreSQL shell
make backup               # Backup database to backups/
make restore BACKUP=...   # Restore from backup

# Testing
make test                 # Run backend tests
make test-ui              # Run frontend tests (Phase 2+)
```

---

## 🔑 Configuration

All configuration is in `.env` (created from `.env.example`).

### Key Settings

```bash
# Security (CHANGE THESE!)
POSTGRES_PASSWORD=...
ADMIN_TOKEN=...
DEBUG_TOKEN=...
JWT_SECRET=...

# Retrieval tuning
ALPHA_VEC=0.55           # Vector weight
BETA_BM25=0.25           # Lexical weight
GAMMA_GRAPH=0.15         # Graph weight
DELTA_RECENCY=0.05       # Recency weight
MMR_LAMBDA=0.7           # Diversity balance

# Ports (if conflicts)
API_PORT=8080
USER_APP_PORT=3000
ADMIN_DASHBOARD_PORT=3001
POSTGRES_PORT=5433
```

After editing `.env`, restart:
```bash
make restart
```

---

## 🧪 Testing the System

### 1. Check Backend Health
```bash
make verify
```

Expected output:
```
✓ postgres               (running)
✓ api                    (running)
✓ retrieval              (running)
✓ API Gateway Health     ✓ (200)
✓ PostgreSQL             ✓ (accepting connections)
✓ Migrations             ✓ (13 applied)
```

### 2. Test Query API
```bash
# Ingest test data
curl -X POST http://localhost:8080/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "event_type": "test.ingested",
    "text_utf8": "The ContinuuAI memory system uses hybrid retrieval with vector, lexical, and graph search.",
    "source_system": "test",
    "source_uri": "test://demo"
  }'

# Query it back
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "00000000-0000-0000-0000-000000000000",
    "principal_id": "00000000-0000-0000-0000-000000000001",
    "mode": "recall",
    "query_text": "How does ContinuuAI retrieve information?"
  }'
```

### 3. Run Test Suite
```bash
make test
```

---

## 🐛 Troubleshooting

### Services won't start
```bash
# Check logs for errors
make logs

# Check specific service
docker compose logs <service_name>

# Restart with fresh state
make restart
```

### Port conflicts
Edit `.env` and change port numbers:
```bash
API_PORT=9080
USER_APP_PORT=4000
ADMIN_DASHBOARD_PORT=4001
POSTGRES_PORT=6433
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check connection
make shell-db

# Reset database (⚠️  destroys data)
docker compose down -v postgres
docker compose up -d postgres
```

### "Out of memory" errors
Add resource limits to `.env`:
```bash
CPU_LIMIT=4
MEMORY_LIMIT=8g
```

### Tests failing
```bash
# Clean and rebuild
make clean
make build
make deploy
make test
```

---

## 📦 System Requirements

### Minimum
- **OS**: Linux (Ubuntu 20.04+) or macOS (12+)
- **Docker**: 24.0+
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 5 GB free

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 20+ GB free
- **GPU**: NVIDIA GPU (for Phase 5 LLM integration)

---

## 🔄 Updates

### Update Docker Images
```bash
make update      # Pull latest images
make restart     # Apply updates
```

### Update Code
```bash
git pull
make build       # Rebuild services
make restart
```

---

## 🚀 Production Deployment

### Security Checklist
- [ ] Change all default passwords in `.env`
- [ ] Enable firewall (only expose needed ports)
- [ ] Use HTTPS (add nginx reverse proxy)
- [ ] Set `REQUIRE_AUTH=true`
- [ ] Disable `DEV_MODE`
- [ ] Enable automated backups (`cron` + `make backup`)
- [ ] Set up monitoring (Prometheus/Grafana)

### Environment-Specific Configs

**Production `.env`:**
```bash
ENV=production
RESTART_POLICY=always
LOG_LEVEL=INFO
REQUIRE_AUTH=true
DEV_MODE=false
```

**Development `.env`:**
```bash
ENV=development
RESTART_POLICY=no
LOG_LEVEL=DEBUG
REQUIRE_AUTH=false
DEV_MODE=true
```

---

## 📚 Next Steps

1. **Phase 1 Complete**: Backend + installer ✅
2. **Phase 2**: Build [Admin Dashboard](docs/operations/ADMIN_DASHBOARD.md)
3. **Phase 3**: Build [User App](docs/tutorials/USER_APP.md)
4. **Phase 4**: Build [Mobile Apps](docs/tutorials/MOBILE_APPS.md)
5. **Phase 5**: Integrate [Real LLM](docs/how-to/LLM_INTEGRATION.md) (requires GPU)

---

## 🆘 Support

- **Documentation**: [docs/README.md](docs/README.md)
- **Issues**: Check logs (`make logs`)
- **Reset**: `make reset` (⚠️  destroys all data)

---

**Status**: Phase 1 Complete (Backend Foundation)  
**Ready for**: Frontend development (Phases 2-4)  
**Waiting for**: GPU hardware (Phase 5)
