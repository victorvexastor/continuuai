#!/usr/bin/env bash
set -euo pipefail

# Start fresh (named volume 'pgdata' is used in compose)
docker compose down -v || true

# Bring up DB and migrations
docker compose up -d postgres
# wait for health
until docker compose exec -T postgres pg_isready -U continuuai -d continuuai; do sleep 1; done

docker compose up -d --build migrate
# wait for migrate container to exit
sleep 1

# Seed minimal data
docker compose up -d --build seed
# wait a moment for seed to exit
sleep 2

# Start embedding and retrieval services
docker compose up -d --build embedding retrieval graph-deriver

# Wait for retrieval to be ready
for i in {1..30}; do
  if curl -sf http://localhost:8081/v1/health >/dev/null; then break; fi
  sleep 1
done

# Smoke retrieval
curl -s -X POST http://localhost:8081/v1/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"org_id":"00000000-0000-0000-0000-000000000000","principal_id":"d5f99e45-b729-4ac0-8101-c972acfd883b","mode":"recall","query_text":"vendor selection","scopes":[]}' | jq '.debug.returned' | grep -E '^[1-9][0-9]*$'

echo "CI greenfield smoke OK"
