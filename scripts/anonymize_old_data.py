#!/usr/bin/env python3
"""
RGPD Compliance - Automatic Anonymization Script

Anonymizes personal data in transactions older than 90 days.
Complies with RGPD Article 5(1)(e) - storage limitation principle.

Usage:
    python scripts/anonymize_old_data.py [--dry-run] [--days=90]

Schedule with cron:
    0 2 * * * /usr/bin/python3 /path/to/scripts/anonymize_old_data.py
"""
import asyncio
import asyncpg
import argparse
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# PostgreSQL connection
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "safeguard"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres_dev"),
}


def anonymize_value(value: str, field_name: str) -> str:
    """
    Anonymize a value using SHA-256 hash.

    Args:
        value: Original value to anonymize
        field_name: Name of the field (for salt)

    Returns:
        Anonymized value (SHA-256 hash)

    Example:
        >>> anonymize_value("192.168.1.1", "ip")
        'ANON_a3f5...'
    """
    if not value or value.startswith("ANON_"):
        return value

    # Create hash with salt
    salt = f"safeguard-{field_name}"
    hashed = hashlib.sha256(f"{value}{salt}".encode()).hexdigest()[:16]
    return f"ANON_{hashed}"


def anonymize_json_field(json_data: Dict[str, Any], fields_to_anonymize: List[str]) -> Dict[str, Any]:
    """
    Anonymize specific fields within a JSON object.

    Args:
        json_data: JSON data containing fields to anonymize
        fields_to_anonymize: List of field names to anonymize

    Returns:
        JSON with anonymized fields
    """
    if not json_data:
        return json_data

    result = json_data.copy()

    for field in fields_to_anonymize:
        if field in result and result[field]:
            result[field] = anonymize_value(str(result[field]), field)

    # Handle nested objects
    if "user" in result and isinstance(result["user"], dict):
        if "user_id" in result["user"]:
            result["user"]["user_id"] = anonymize_value(str(result["user"]["user_id"]), "user_id")

    if "context" in result and isinstance(result["context"], dict):
        if "ip" in result["context"]:
            result["context"]["ip"] = anonymize_value(result["context"]["ip"], "ip")

    if "card" in result and isinstance(result["card"], dict):
        if "user_id" in result["card"]:
            result["card"]["user_id"] = anonymize_value(str(result["card"]["user_id"]), "user_id")

    return result


async def anonymize_transactions(pool: asyncpg.Pool, days: int = 90, dry_run: bool = False) -> Dict[str, int]:
    """
    Anonymize transactions older than specified days.

    Args:
        pool: PostgreSQL connection pool
        days: Number of days after which to anonymize (default: 90)
        dry_run: If True, only count records without modifying

    Returns:
        Statistics dictionary
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}RGPD Anonymization - Transactions older than {days} days")
    print(f"Cutoff date: {cutoff_date.isoformat()}")
    print("=" * 60)

    # Count records to anonymize
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE created_at < $1
              AND (
                  ip_address IS NOT NULL
                  OR user_id IS NOT NULL
                  OR transaction_data::text LIKE '%ip%'
              )
            """,
            cutoff_date
        )

    print(f"Found {count} transactions to anonymize")

    if count == 0:
        print("No transactions to anonymize.")
        return {"total": 0, "anonymized": 0}

    if dry_run:
        print("[DRY RUN] Would anonymize these records. Run without --dry-run to execute.")
        return {"total": count, "anonymized": 0}

    # Anonymize transactions
    anonymized = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Fetch old transactions
            rows = await conn.fetch(
                """
                SELECT transaction_id, user_id, ip_address, transaction_data
                FROM transactions
                WHERE created_at < $1
                  AND (
                      ip_address IS NOT NULL
                      OR user_id IS NOT NULL
                  )
                FOR UPDATE
                """,
                cutoff_date
            )

            for row in rows:
                transaction_id = row["transaction_id"]
                user_id = row["user_id"]
                ip_address = row["ip_address"]
                transaction_data = row["transaction_data"]

                # Anonymize fields
                new_user_id = anonymize_value(user_id, "user_id") if user_id else None
                new_ip = anonymize_value(ip_address, "ip") if ip_address else None

                # Anonymize JSON data
                new_data = anonymize_json_field(
                    transaction_data,
                    ["user_id", "ip", "ip_address"]
                )

                # Update transaction
                await conn.execute(
                    """
                    UPDATE transactions
                    SET user_id = $1,
                        ip_address = $2,
                        transaction_data = $3
                    WHERE transaction_id = $4
                    """,
                    new_user_id,
                    new_ip,
                    new_data,
                    transaction_id
                )

                anonymized += 1

                if anonymized % 100 == 0:
                    print(f"Anonymized {anonymized}/{count} transactions...")

    print(f"\n✓ Successfully anonymized {anonymized} transactions")
    return {"total": count, "anonymized": anonymized}


async def anonymize_audit_logs(pool: asyncpg.Pool, days: int = 90, dry_run: bool = False) -> Dict[str, int]:
    """
    Anonymize audit logs older than specified days.

    Note: We can only anonymize the 'after' field since audit_logs is WORM.
    We create a separate anonymized copy for compliance.

    Args:
        pool: PostgreSQL connection pool
        days: Number of days after which to anonymize (default: 90)
        dry_run: If True, only count records without modifying

    Returns:
        Statistics dictionary
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}RGPD Anonymization - Audit Logs older than {days} days")
    print(f"Cutoff date: {cutoff_date.isoformat()}")
    print("=" * 60)

    # Count records to anonymize
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE ts < $1
              AND after IS NOT NULL
              AND after::text LIKE '%ip%'
            """,
            cutoff_date
        )

    print(f"Found {count} audit log entries with IP addresses")
    print("Note: Audit logs are WORM (immutable), creating anonymized view...")

    if count == 0:
        print("No audit logs to anonymize.")
        return {"total": 0, "anonymized": 0}

    if dry_run:
        print("[DRY RUN] Would create anonymized view. Run without --dry-run to execute.")
        return {"total": count, "anonymized": 0}

    # Create materialized view with anonymized audit logs
    async with pool.acquire() as conn:
        await conn.execute(
            """
            DROP MATERIALIZED VIEW IF EXISTS audit_logs_anonymized;

            CREATE MATERIALIZED VIEW audit_logs_anonymized AS
            SELECT
                log_id,
                actor,
                action,
                entity,
                entity_id,
                before,
                CASE
                    WHEN ts < $1 THEN
                        -- Anonymize IP addresses in JSON
                        regexp_replace(
                            after::text,
                            '"ip_address":\\s*"[^"]+"',
                            '"ip_address": "ANONYMIZED"',
                            'g'
                        )::jsonb
                    ELSE after
                END as after,
                ts,
                signature,
                prev_log_hash
            FROM audit_logs;

            CREATE INDEX idx_audit_logs_anonymized_ts ON audit_logs_anonymized(ts);
            CREATE INDEX idx_audit_logs_anonymized_entity ON audit_logs_anonymized(entity, entity_id);
            """,
            cutoff_date
        )

    print(f"✓ Created anonymized materialized view 'audit_logs_anonymized'")
    print(f"  Use: SELECT * FROM audit_logs_anonymized WHERE ts < NOW() - INTERVAL '{days} days';")

    return {"total": count, "anonymized": count}


async def log_dpia_event(pool: asyncpg.Pool, event: str, details: Dict[str, Any]):
    """
    Log DPIA (Data Protection Impact Assessment) event.

    Args:
        pool: PostgreSQL connection pool
        event: Event name
        details: Event details
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO dpia_logs (event, details, ts)
            VALUES ($1, $2, NOW())
            """,
            event,
            details
        )


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Anonymize personal data older than specified days (RGPD compliance)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be anonymized without actually doing it"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Anonymize data older than this many days (default: 90)"
    )
    parser.add_argument(
        "--skip-audit-logs",
        action="store_true",
        help="Skip anonymizing audit logs (only anonymize transactions)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("RGPD COMPLIANCE - DATA ANONYMIZATION SCRIPT")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'EXECUTION (will modify data)'}")
    print(f"Retention period: {args.days} days")
    print("=" * 60)

    # Connect to PostgreSQL
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=5)
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return 1

    try:
        # Anonymize transactions
        tx_stats = await anonymize_transactions(pool, days=args.days, dry_run=args.dry_run)

        # Anonymize audit logs
        if not args.skip_audit_logs:
            audit_stats = await anonymize_audit_logs(pool, days=args.days, dry_run=args.dry_run)
        else:
            audit_stats = {"total": 0, "anonymized": 0}

        # Log DPIA event
        if not args.dry_run:
            await log_dpia_event(
                pool,
                "DATA_ANONYMIZATION",
                {
                    "days": args.days,
                    "transactions_anonymized": tx_stats["anonymized"],
                    "audit_logs_processed": audit_stats["anonymized"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Transactions anonymized: {tx_stats['anonymized']}/{tx_stats['total']}")
        print(f"Audit logs processed: {audit_stats['anonymized']}/{audit_stats['total']}")

        if not args.dry_run:
            print("\n✓ RGPD anonymization completed successfully")
            print("  Data older than {} days has been anonymized".format(args.days))
        else:
            print("\n[DRY RUN] No data was modified. Run without --dry-run to execute.")

        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n✗ Error during anonymization: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await pool.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
