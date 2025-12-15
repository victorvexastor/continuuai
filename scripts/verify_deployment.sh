#!/usr/bin/env bash
set -euo pipefail

# ContinuuAI Deployment Verification Script
# Checks health of all services

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0

check() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"
  
  printf "  %-25s" "$name"
  
  if response=$(curl -sf -w "%{http_code}" -o /dev/null "$url" 2>/dev/null); then
    if [ "$response" = "$expected" ]; then
      echo -e "${GREEN}✓${NC} ($response)"
      PASSED=$((PASSED + 1))
    else
      echo -e "${YELLOW}⚠${NC} (got $response, expected $expected)"
      FAILED=$((FAILED + 1))
    fi
  else
    echo -e "${RED}✗${NC} (unreachable)"
    FAILED=$((FAILED + 1))
  fi
}

check_docker_service() {
  local service="$1"
  local container_name="${2:-continuuai-${service}-1}"
  
  printf "  %-25s" "$service"
  
  if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
    echo -e "${GREEN}✓${NC} (running)"
    PASSED=$((PASSED + 1))
  else
    echo -e "${RED}✗${NC} (not running)"
    FAILED=$((FAILED + 1))
  fi
}

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║        ContinuuAI Deployment Verification             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check Docker containers
echo "🐳 Docker Containers:"
check_docker_service "postgres"
check_docker_service "api" "continuuai-api-1"
check_docker_service "retrieval"
check_docker_service "inference"
check_docker_service "embedding"
check_docker_service "graph-deriver"

echo ""
echo "🌐 HTTP Endpoints:"

# Check API endpoints
check "API Gateway Health" "http://localhost:8080/healthz"
check "Retrieval Service" "http://localhost:8081/v1/health"
check "Inference Service" "http://localhost:8082/healthz" "404"  # No healthz yet
check "Embedding Service" "http://localhost:8083/healthz" "404"  # No healthz yet

# Future: check frontends when they exist
# check "User App" "http://localhost:3000"
# check "Admin Dashboard" "http://localhost:3001"

echo ""
echo "📊 Database:"

# Check PostgreSQL
if docker compose exec -T postgres pg_isready -U continuuai -d continuuai &>/dev/null; then
  echo -e "  PostgreSQL              ${GREEN}✓${NC} (accepting connections)"
  PASSED=$((PASSED + 1))
else
  echo -e "  PostgreSQL              ${RED}✗${NC} (not ready)"
  FAILED=$((FAILED + 1))
fi

# Check migrations
MIGRATION_COUNT=$(docker compose exec -T postgres psql -U continuuai -d continuuai -tAc "SELECT COUNT(*) FROM schema_version" 2>/dev/null || echo "0")
if [ "$MIGRATION_COUNT" -ge 13 ]; then
  echo -e "  Migrations              ${GREEN}✓${NC} ($MIGRATION_COUNT applied)"
  PASSED=$((PASSED + 1))
else
  echo -e "  Migrations              ${YELLOW}⚠${NC} (only $MIGRATION_COUNT applied, expected 13+)"
  FAILED=$((FAILED + 1))
fi

# Check seeded data
ORG_COUNT=$(docker compose exec -T postgres psql -U continuuai -d continuuai -tAc "SELECT COUNT(*) FROM organisation" 2>/dev/null || echo "0")
if [ "$ORG_COUNT" -ge 1 ]; then
  echo -e "  Seed Data               ${GREEN}✓${NC} ($ORG_COUNT org(s))"
  PASSED=$((PASSED + 1))
else
  echo -e "  Seed Data               ${YELLOW}⚠${NC} (no orgs found)"
  FAILED=$((FAILED + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════════"

TOTAL=$((PASSED + FAILED))
if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All checks passed!${NC} ($PASSED/$TOTAL)"
  exit 0
else
  echo -e "${YELLOW}⚠️  Some checks failed${NC} ($PASSED/$TOTAL passed, $FAILED failed)"
  echo ""
  echo "Troubleshooting:"
  echo "  • Check logs:      make logs"
  echo "  • Check status:    docker compose ps"
  echo "  • Restart:         make restart"
  exit 1
fi
