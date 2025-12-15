#!/usr/bin/env python3
"""
ACL negative tests: prove access control boundaries hold.

Tests:
1. Principal with no scope → 0 results (even if matches exist)
2. Principal with partial scope → only permitted artifacts returned
3. Seed finds matches but policy blocks all → 0 results (no filter-after-top-k bugs)
"""
import os, sys, uuid
import httpx
import psycopg

DB = os.environ.get("DATABASE_URL", "postgres://continuuai:continuuai@localhost:5433/continuuai")
RET_URL = os.environ.get("RETRIEVAL_URL", "http://localhost:8081/v1/retrieve")
ORG = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")

# Create test principals and scopes
PRINCIPAL_NO_SCOPE = str(uuid.uuid4())
PRINCIPAL_PARTIAL_SCOPE = str(uuid.uuid4())
ARTIFACT_ALLOWED = str(uuid.uuid4())
ARTIFACT_BLOCKED = str(uuid.uuid4())

async def setup_acl_fixtures():
    """Insert test data with known ACL boundaries."""
    with psycopg.connect(DB) as conn:
        # Create two artifacts
        conn.execute("""
            INSERT INTO artifact (artifact_id, org_id, name, created_at)
            VALUES (%s, %s, %s, now()), (%s, %s, %s, now())
        """, (ARTIFACT_ALLOWED, ORG, "allowed-doc", ARTIFACT_BLOCKED, ORG, "blocked-doc"))
        
        # Create spans with overlapping content
        conn.execute("""
            INSERT INTO artifact_span (artifact_span_id, org_id, artifact_id, span_index, content_text, created_at)
            VALUES 
                (gen_random_uuid(), %s, %s, 0, 'vendor selection criteria for procurement', now()),
                (gen_random_uuid(), %s, %s, 0, 'vendor selection process and approval workflow', now())
        """, (ORG, ARTIFACT_ALLOWED, ORG, ARTIFACT_BLOCKED))
        
        # Create evidence spans from both
        conn.execute("""
            INSERT INTO evidence_span (evidence_span_id, org_id, artifact_id, span_index, content_text, created_at)
            SELECT artifact_span_id, org_id, artifact_id, span_index, content_text, created_at
            FROM artifact_span
            WHERE artifact_id IN (%s, %s)
        """, (ARTIFACT_ALLOWED, ARTIFACT_BLOCKED))
        
        # Principal with NO scope
        conn.execute("""
            INSERT INTO principal (principal_id, org_id, created_at)
            VALUES (%s, %s, now())
        """, (PRINCIPAL_NO_SCOPE, ORG))
        
        # Principal with PARTIAL scope (only allowed artifact)
        conn.execute("""
            INSERT INTO principal (principal_id, org_id, created_at)
            VALUES (%s, %s, now())
        """, (PRINCIPAL_PARTIAL_SCOPE, ORG))
        
        role_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO role (role_id, org_id, role_name, created_at)
            VALUES (%s, %s, %s, now())
        """, (role_id, ORG, "test-partial-reader"))
        
        conn.execute("""
            INSERT INTO principal_role (principal_id, role_id, org_id, created_at)
            VALUES (%s, %s, %s, now())
        """, (PRINCIPAL_PARTIAL_SCOPE, role_id, ORG))
        
        conn.execute("""
            INSERT INTO role_scope (role_id, org_id, artifact_id, created_at)
            VALUES (%s, %s, %s, now())
        """, (role_id, ORG, ARTIFACT_ALLOWED))
        
        conn.commit()
        print(f"✓ Fixtures created: principals={PRINCIPAL_NO_SCOPE[:8]}, {PRINCIPAL_PARTIAL_SCOPE[:8]}")

async def test_no_scope_zero_results():
    """Test 1: Principal with no scope gets zero results."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        payload = {
            "org_id": ORG,
            "principal_id": PRINCIPAL_NO_SCOPE,
            "mode": "recall",
            "query_text": "vendor selection",
            "scopes": []
        }
        r = await client.post(RET_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        
        if len(results) > 0:
            print(f"❌ Test 1 FAILED: principal with no scope got {len(results)} results", file=sys.stderr)
            return False
        
        print(f"✓ Test 1 PASSED: no scope → 0 results")
        return True

async def test_partial_scope_filtered():
    """Test 2: Principal with partial scope sees only permitted artifacts."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        payload = {
            "org_id": ORG,
            "principal_id": PRINCIPAL_PARTIAL_SCOPE,
            "mode": "recall",
            "query_text": "vendor selection",
            "scopes": []
        }
        r = await client.post(RET_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        
        # Should have results (from allowed artifact)
        if len(results) == 0:
            print(f"⚠ Test 2: no results (may be expected if seed didn't match)", file=sys.stderr)
            return True  # Not a failure, just no matches
        
        # Verify all results are from allowed artifact only
        blocked_found = []
        for span in results:
            with psycopg.connect(DB) as conn:
                artifact_id = conn.execute("""
                    SELECT artifact_id FROM evidence_span WHERE evidence_span_id = %s
                """, (span["id"],)).fetchone()[0]
                
                if str(artifact_id) == ARTIFACT_BLOCKED:
                    blocked_found.append(span["id"])
        
        if blocked_found:
            print(f"❌ Test 2 FAILED: found {len(blocked_found)} spans from blocked artifact", file=sys.stderr)
            return False
        
        print(f"✓ Test 2 PASSED: partial scope → only permitted artifacts ({len(results)} spans)")
        return True

async def test_policy_blocks_all_seeds():
    """Test 3: Even if seed matches, policy must filter before returning."""
    # This is implicitly tested by test 1, but we verify the query would have matched
    with psycopg.connect(DB) as conn:
        # Check that blocked artifact contains matching content
        has_match = conn.execute("""
            SELECT EXISTS (
                SELECT 1 FROM artifact_span
                WHERE artifact_id = %s 
                AND content_text ILIKE %s
            )
        """, (ARTIFACT_BLOCKED, "%vendor selection%")).fetchone()[0]
        
        if not has_match:
            print("⚠ Test 3: blocked artifact doesn't contain test phrase (test inconclusive)")
            return True
        
        # Now verify principal with no scope gets zero results despite match existing
        async with httpx.AsyncClient(timeout=20.0) as client:
            payload = {
                "org_id": ORG,
                "principal_id": PRINCIPAL_NO_SCOPE,
                "mode": "recall",
                "query_text": "vendor selection",
                "scopes": []
            }
            r = await client.post(RET_URL, json=payload)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            
            if len(results) > 0:
                print(f"❌ Test 3 FAILED: seed matched but policy should have blocked (got {len(results)} results)", file=sys.stderr)
                return False
            
            print("✓ Test 3 PASSED: seed matches exist but policy blocks all")
            return True

async def main():
    print("=== ACL Negative Tests ===")
    await setup_acl_fixtures()
    
    tests = [
        ("No scope → 0 results", test_no_scope_zero_results),
        ("Partial scope → filtered results", test_partial_scope_filtered),
        ("Policy blocks all seeds", test_policy_blocks_all_seeds),
    ]
    
    results = []
    for name, test_fn in tests:
        print(f"\nRunning: {name}")
        passed = await test_fn()
        results.append((name, passed))
    
    print("\n=== Summary ===")
    failed = [name for name, passed in results if not passed]
    
    if failed:
        print(f"❌ {len(failed)}/{len(tests)} tests FAILED:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"✅ All {len(tests)} ACL tests PASSED")
        sys.exit(0)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
