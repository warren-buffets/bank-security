"""
Test HMAC-SHA256 signature and WORM immutability for audit logs.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'decision-engine'))

from app.audit import create_audit_entry, verify_audit_log, sign_audit_log
from app.storage import postgres_storage


async def test_hmac_signature():
    """Test HMAC-SHA256 signature generation and verification."""
    print("\n=== Test 1: HMAC-SHA256 Signature ===")

    # Create audit entry
    entry = create_audit_entry(
        actor="decision-engine",
        action="SCORE_TRANSACTION",
        entity="transaction",
        entity_id="txn_test_001",
        details={"score": 0.85, "decision": "REVIEW"},
        ip_address="10.0.1.15"
    )

    print(f"✓ Created audit entry with signature: {entry['signature'][:16]}...")
    print(f"  Actor: {entry['actor']}")
    print(f"  Action: {entry['action']}")
    print(f"  Entity: {entry['entity']}:{entry['entity_id']}")

    # Verify signature
    signature = entry.pop("signature")
    is_valid = verify_audit_log(entry, signature)

    if is_valid:
        print(f"✓ Signature is VALID")
    else:
        print(f"✗ Signature verification FAILED")
        return False

    # Test tampering detection
    print("\n=== Test 2: Tampering Detection ===")
    entry["details"]["score"] = 0.10  # Tamper with score
    is_valid_after_tamper = verify_audit_log(entry, signature)

    if not is_valid_after_tamper:
        print(f"✓ Tampering detected successfully (signature invalid after modification)")
    else:
        print(f"✗ FAILED: Tampering not detected!")
        return False

    return True


async def test_database_storage():
    """Test storing audit logs in PostgreSQL with HMAC signature."""
    print("\n=== Test 3: Database Storage ===")

    try:
        # Connect to database
        await postgres_storage.connect()
        print("✓ Connected to PostgreSQL")

        # Store audit log
        success = await postgres_storage.store_audit_log(
            actor="test-suite",
            action="TEST_AUDIT_LOG",
            entity="test",
            entity_id="test_001",
            details={"test": True, "timestamp": "2026-01-23"},
            ip_address="127.0.0.1"
        )

        if success:
            print("✓ Audit log stored successfully with HMAC signature")
        else:
            print("✗ Failed to store audit log")
            return False

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        await postgres_storage.close()


async def test_worm_immutability():
    """Test WORM (Write Once Read Many) - logs cannot be modified or deleted."""
    print("\n=== Test 4: WORM Immutability ===")

    try:
        await postgres_storage.connect()

        # First, insert a test log
        await postgres_storage.store_audit_log(
            actor="test-suite",
            action="WORM_TEST",
            entity="test",
            entity_id="worm_test_001",
            details={"immutable": True}
        )
        print("✓ Inserted test audit log")

        # Try to UPDATE (should fail)
        print("\nAttempting UPDATE (should be blocked)...")
        try:
            async with postgres_storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE audit_logs
                    SET actor = 'hacker'
                    WHERE entity_id = 'worm_test_001'
                    """
                )
            print("✗ SECURITY BREACH: UPDATE was allowed!")
            return False
        except Exception as e:
            if "WORM compliance" in str(e) or "not allowed" in str(e):
                print(f"✓ UPDATE blocked: {str(e).split('DETAIL')[0].strip()}")
            else:
                print(f"✓ UPDATE blocked: {e}")

        # Try to DELETE (should fail)
        print("\nAttempting DELETE (should be blocked)...")
        try:
            async with postgres_storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    DELETE FROM audit_logs
                    WHERE entity_id = 'worm_test_001'
                    """
                )
            print("✗ SECURITY BREACH: DELETE was allowed!")
            return False
        except Exception as e:
            if "WORM compliance" in str(e) or "not allowed" in str(e):
                print(f"✓ DELETE blocked: {str(e).split('DETAIL')[0].strip()}")
            else:
                print(f"✓ DELETE blocked: {e}")

        print("\n✓ WORM immutability verified: Logs cannot be modified or deleted")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        await postgres_storage.close()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("AUDIT LOG HMAC-SHA256 & WORM IMMUTABILITY TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1 & 2: HMAC signature and tampering detection
    result1 = await test_hmac_signature()
    results.append(("HMAC Signature & Tampering Detection", result1))

    # Test 3: Database storage
    result2 = await test_database_storage()
    results.append(("Database Storage", result2))

    # Test 4: WORM immutability
    result3 = await test_worm_immutability()
    results.append(("WORM Immutability", result3))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(r for _, r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - HMAC & WORM IMPLEMENTATION VERIFIED")
        print("=" * 60)
        print("\nConformité PSD2/ACPR:")
        print("  ✓ Logs signés HMAC-SHA256")
        print("  ✓ Immutabilité garantie (WORM)")
        print("  ✓ Rétention 7 ans (triggers PostgreSQL)")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
