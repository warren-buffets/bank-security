"""
Audit logging with HMAC-SHA256 signature for immutability.
Implements WORM (Write Once Read Many) compliance for PSD2/ACPR.
"""
import hmac
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Any


# Secret key for HMAC signature (should be in env variable in production)
HMAC_SECRET = os.getenv("AUDIT_HMAC_SECRET", "safeguard-audit-secret-key-change-in-prod")


def sign_audit_log(data: Dict[str, Any]) -> str:
    """
    Generate HMAC-SHA256 signature for audit log entry.

    Args:
        data: Dictionary containing audit log fields

    Returns:
        Hexadecimal HMAC-SHA256 signature

    Example:
        >>> data = {
        ...     "actor": "decision-engine",
        ...     "action": "SCORE_TRANSACTION",
        ...     "entity": "transaction",
        ...     "entity_id": "txn_123"
        ... }
        >>> signature = sign_audit_log(data)
        >>> len(signature)
        64
    """
    # Sort keys to ensure consistent signature
    canonical_message = json.dumps(data, sort_keys=True, separators=(',', ':'))

    # Create HMAC-SHA256 signature
    signature = hmac.new(
        HMAC_SECRET.encode('utf-8'),
        canonical_message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_audit_log(data: Dict[str, Any], signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature of audit log entry.

    Args:
        data: Dictionary containing audit log fields
        signature: Expected HMAC-SHA256 signature

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> data = {"actor": "test", "action": "TEST"}
        >>> sig = sign_audit_log(data)
        >>> verify_audit_log(data, sig)
        True
        >>> verify_audit_log(data, "invalid_signature")
        False
    """
    expected_signature = sign_audit_log(data)
    return hmac.compare_digest(expected_signature, signature)


def create_audit_entry(
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    details: Dict[str, Any] = None,
    ip_address: str = None
) -> Dict[str, Any]:
    """
    Create a complete audit log entry with HMAC signature.

    Args:
        actor: Who performed the action (service, user, system)
        action: What action was performed
        entity: What type of entity was affected
        entity_id: ID of the affected entity
        details: Additional details (optional)
        ip_address: IP address of the actor (optional)

    Returns:
        Complete audit entry with signature

    Example:
        >>> entry = create_audit_entry(
        ...     actor="decision-engine",
        ...     action="SCORE_TRANSACTION",
        ...     entity="transaction",
        ...     entity_id="txn_123",
        ...     details={"score": 0.85, "decision": "REVIEW"}
        ... )
        >>> "signature" in entry
        True
        >>> "timestamp" in entry
        True
    """
    # Create base entry
    entry = {
        "actor": actor,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "details": details or {},
        "ip_address": ip_address
    }

    # Generate signature
    entry["signature"] = sign_audit_log(entry)

    return entry


def validate_audit_integrity(entries: list) -> Dict[str, Any]:
    """
    Validate integrity of multiple audit log entries.

    Args:
        entries: List of audit log entries with signatures

    Returns:
        Validation report with statistics

    Example:
        >>> entries = [
        ...     create_audit_entry("sys", "TEST", "test", "1"),
        ...     create_audit_entry("sys", "TEST", "test", "2")
        ... ]
        >>> report = validate_audit_integrity(entries)
        >>> report["total"]
        2
        >>> report["valid"]
        2
    """
    total = len(entries)
    valid = 0
    invalid = []

    for i, entry in enumerate(entries):
        signature = entry.pop("signature", None)
        if signature and verify_audit_log(entry, signature):
            valid += 1
        else:
            invalid.append({"index": i, "entry_id": entry.get("log_id")})
        # Restore signature
        if signature:
            entry["signature"] = signature

    return {
        "total": total,
        "valid": valid,
        "invalid": len(invalid),
        "invalid_entries": invalid,
        "integrity_percentage": (valid / total * 100) if total > 0 else 0
    }


# Example usage and testing
if __name__ == "__main__":
    # Create sample audit entry
    entry = create_audit_entry(
        actor="decision-engine",
        action="SCORE_TRANSACTION",
        entity="transaction",
        entity_id="txn_abc123",
        details={
            "score": 0.85,
            "decision": "REVIEW",
            "latency_ms": 87
        },
        ip_address="10.0.1.15"
    )

    print("Sample Audit Entry:")
    print(json.dumps(entry, indent=2))

    # Verify signature
    signature = entry.pop("signature")
    is_valid = verify_audit_log(entry, signature)
    print(f"\nSignature valid: {is_valid}")

    # Try to tamper
    entry["details"]["score"] = 0.10  # Tamper with score
    is_valid_after_tamper = verify_audit_log(entry, signature)
    print(f"Signature valid after tampering: {is_valid_after_tamper}")
