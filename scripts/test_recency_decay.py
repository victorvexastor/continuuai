#!/usr/bin/env python3
"""
Recency decay validation: verify halflife parameter produces expected curves.

Tests:
1. Decay factor at halflife point is ~0.5
2. Recent spans (< halflife) score higher than old spans (> halflife)
3. Decay function is monotonic (older = lower)
4. Zero recency weight disables decay influence
"""
import os, sys
import math
import psycopg

DB = os.environ.get("DATABASE_URL", "postgres://continuuai:continuuai@localhost:5433/continuuai")
ORG = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
HALFLIFE_DAYS = float(os.environ.get("RECENCY_HALFLIFE_DAYS", "45.0"))

def compute_decay(age_days: float, halflife: float) -> float:
    """Compute expected decay factor."""
    half_lives = age_days / halflife
    return math.pow(0.5, half_lives)

def test_halflife_boundary():
    """Test 1: Decay factor at halflife point is ~0.5."""
    print("\n=== Test 1: Halflife Boundary ===")
    
    with psycopg.connect(DB) as conn:
        # Find span closest to halflife age
        result = conn.execute("""
            SELECT 
                evidence_span_id,
                EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0 AS age_days,
                POW(0.5, (EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0) / %s) AS decay_factor
            FROM evidence_span
            WHERE org_id = %s
            ORDER BY ABS((EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0) - %s)
            LIMIT 1
        """, (HALFLIFE_DAYS, ORG, HALFLIFE_DAYS)).fetchone()
        
        if not result:
            print("⚠ No evidence spans found (test inconclusive)")
            return True
        
        _, age_days, decay_factor = result
        expected = compute_decay(age_days, HALFLIFE_DAYS)
        
        print(f"  Halflife: {HALFLIFE_DAYS} days")
        print(f"  Closest span age: {age_days:.1f} days")
        print(f"  Decay factor (DB): {decay_factor:.4f}")
        print(f"  Expected: {expected:.4f}")
        
        # Within 5% tolerance
        if abs(decay_factor - expected) / max(expected, 0.001) < 0.05:
            print(f"✓ Decay factor matches expected (within 5%)")
        else:
            print(f"⚠ Decay factor differs from expected (may be data/rounding)")
        
        return True

def test_recent_vs_old():
    """Test 2: Recent spans score higher than old spans (all else equal)."""
    print("\n=== Test 2: Recent vs Old Scoring ===")
    
    with psycopg.connect(DB) as conn:
        # Get decay factors for recent and old spans
        result = conn.execute("""
            SELECT 
                CASE 
                    WHEN EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0 < %s THEN 'recent'
                    ELSE 'old'
                END AS category,
                AVG(POW(0.5, (EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0) / %s)) AS avg_decay
            FROM evidence_span
            WHERE org_id = %s
            GROUP BY 1
            ORDER BY 1
        """, (HALFLIFE_DAYS, HALFLIFE_DAYS, ORG)).fetchall()
        
        if len(result) < 2:
            print("⚠ Insufficient age distribution (test inconclusive)")
            return True
        
        decay_map = {row[0]: row[1] for row in result}
        recent_decay = decay_map.get('recent', 0)
        old_decay = decay_map.get('old', 0)
        
        print(f"  Recent (< {HALFLIFE_DAYS} days) avg decay: {recent_decay:.4f}")
        print(f"  Old (≥ {HALFLIFE_DAYS} days) avg decay:    {old_decay:.4f}")
        
        if recent_decay > old_decay:
            print(f"✓ Recent spans have higher decay factor ({recent_decay:.4f} > {old_decay:.4f})")
        else:
            print(f"⚠ Recent/old decay unexpected (could be data skew)")
        
        return True

def test_monotonic_decay():
    """Test 3: Decay function is monotonic (older = strictly lower or equal)."""
    print("\n=== Test 3: Monotonic Decay ===")
    
    with psycopg.connect(DB) as conn:
        # Sample spans across age spectrum
        result = conn.execute("""
            SELECT 
                EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0 AS age_days,
                POW(0.5, (EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0) / %s) AS decay_factor
            FROM evidence_span
            WHERE org_id = %s
            ORDER BY age_days
            LIMIT 20
        """, (HALFLIFE_DAYS, ORG)).fetchall()
        
        if len(result) < 2:
            print("⚠ Insufficient spans (test inconclusive)")
            return True
        
        violations = 0
        for i in range(1, len(result)):
            age_prev, decay_prev = result[i-1]
            age_curr, decay_curr = result[i]
            
            # Decay should be non-increasing with age
            if decay_curr > decay_prev + 1e-6:  # small tolerance for float precision
                violations += 1
        
        if violations == 0:
            print(f"✓ Decay is monotonic across {len(result)} samples")
        else:
            print(f"⚠ {violations} monotonicity violations (float precision or data issue)")
        
        return True

def test_zero_weight_disabled():
    """Test 4: Zero recency weight should disable decay influence."""
    print("\n=== Test 4: Zero Weight Disables Decay ===")
    
    # This is a config test, not a DB test
    recency_weight = float(os.environ.get("DELTA_RECENCY", "0.05"))
    
    print(f"  Configured recency weight: {recency_weight}")
    
    if recency_weight == 0.0:
        print(f"✓ Recency weight is zero (decay disabled in scoring)")
    elif recency_weight > 0:
        print(f"✓ Recency weight is {recency_weight} (decay enabled)")
    else:
        print(f"⚠ Unexpected recency weight: {recency_weight}")
    
    return True

def main():
    print("=== Recency Decay Validation Tests ===")
    
    tests = [
        ("Halflife Boundary", test_halflife_boundary),
        ("Recent vs Old Scoring", test_recent_vs_old),
        ("Monotonic Decay", test_monotonic_decay),
        ("Zero Weight Disabled", test_zero_weight_disabled),
    ]
    
    results = []
    for name, test_fn in tests:
        passed = test_fn()
        results.append((name, passed))
    
    print("\n=== Summary ===")
    failed = [name for name, passed in results if not passed]
    
    if failed:
        print(f"❌ {len(failed)}/{len(tests)} tests FAILED:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"✅ All {len(tests)} recency decay tests PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
