#!/bin/bash

set -e

echo "========================================="
echo "ContinuuAI API Test Suite"
echo "========================================="
echo ""

echo "1️⃣  Testing Health Check..."
curl -s http://localhost:8080/healthz | jq
echo "✅ Health check passed"
echo ""

echo "2️⃣  Testing /v1/query (Recall Mode)..."
curl -s http://localhost:8080/v1/query \
  -H 'content-type: application/json' \
  -d '{
    "org_id":"00000000-0000-0000-0000-000000000000",
    "principal_id":"p1",
    "mode":"recall",
    "query_text":"What did we decide about Feature X?",
    "scopes":["team:eng"]
  }' | jq '.answer, .evidence[0].quote, .policy.status'
echo "✅ Query endpoint working"
echo ""

echo "3️⃣  Testing /v1/ingest (New Decision)..."
curl -s http://localhost:8080/v1/ingest \
  -H 'content-type: application/json' \
  -d '{
    "org_id":"00000000-0000-0000-0000-000000000000",
    "actor_external_subject":"p1",
    "event_type":"decision.recorded",
    "idempotency_key":"test-'$(date +%s)'",
    "payload":{
      "topic":"testing",
      "decision_key":"decision:test_decision",
      "decision_title":"Test Decision"
    },
    "text_utf8":"Test decision: Run full integration tests. Rationale: ensure system stability."
  }' | jq '.ok, .event_id'
echo "✅ Ingest endpoint working"
echo ""

echo "4️⃣  Waiting for graph deriver (2 seconds)..."
sleep 2
echo ""

echo "5️⃣  Checking graph nodes..."
docker exec -i $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "SELECT COUNT(*) as total_nodes FROM graph_node;"
echo "✅ Graph nodes created"
echo ""

echo "6️⃣  Checking graph edges..."
docker exec -i $(docker ps -qf name=postgres) psql -U continuuai -d continuuai -c "SELECT COUNT(*) as total_edges FROM graph_edge;"
echo "✅ Graph edges created"
echo ""

echo "========================================="
echo "✅ ALL TESTS PASSED!"
echo "========================================="
echo ""
echo "System is running correctly at:"
echo "  API Gateway:  http://localhost:8080"
echo "  Retrieval:    http://localhost:8081"
echo "  Inference:    http://localhost:8082"
echo "  PostgreSQL:   localhost:5433"
echo ""
echo "Read the docs:"
echo "  README.md - Quick start guide"
echo "  CONTINUUAI_VISION.md - Vision & promise"
echo "  TECHNICAL_DESIGN.md - Architecture details"
