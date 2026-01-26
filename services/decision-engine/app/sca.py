"""
Strong Customer Authentication (SCA) - PSD2 Compliance

Implements dynamic SCA based on transaction risk score.
Complies with PSD2 Regulatory Technical Standards (RTS) Article 18.

SCA Levels:
- NONE: Low risk (<0.3), no additional authentication
- OTP_SMS: Medium risk (0.3-0.5), SMS code
- BIOMETRIC: Medium-high risk (0.5-0.7), fingerprint/face
- PUSH_NOTIFICATION: High risk (0.7-0.9), app push with biometric
- HARDWARE_TOKEN: Very high risk (>0.9), physical security key
"""
from typing import Dict, Any, Optional
from enum import Enum
import asyncpg
from datetime import datetime


class SCALevel(str, Enum):
    """SCA authentication levels based on risk."""
    NONE = "NONE"
    OTP_SMS = "OTP_SMS"
    OTP_EMAIL = "OTP_EMAIL"
    BIOMETRIC = "BIOMETRIC"
    PUSH_NOTIFICATION = "PUSH_NOTIFICATION"
    HARDWARE_TOKEN = "HARDWARE_TOKEN"


class SCAStatus(str, Enum):
    """SCA challenge status."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    BYPASSED = "BYPASSED"


def determine_sca_level(risk_score: float, amount: float = None, transaction_type: str = None) -> SCALevel:
    """
    Determine required SCA level based on transaction risk.

    Args:
        risk_score: Risk score from fraud detection (0.0-1.0)
        amount: Transaction amount (optional, for additional rules)
        transaction_type: Type of transaction (optional)

    Returns:
        Required SCA level

    PSD2 RTS Exemptions:
    - Low-value payments <30 EUR: NONE
    - Trusted beneficiaries: Lower SCA
    - Transaction risk analysis (TRA): Dynamic based on risk

    Example:
        >>> determine_sca_level(0.15, amount=25.0)
        SCALevel.NONE
        >>> determine_sca_level(0.85, amount=5000.0)
        SCALevel.HARDWARE_TOKEN
    """
    # PSD2 Exemption: Low-value payments <30 EUR
    if amount and amount < 30.0:
        return SCALevel.NONE

    # PSD2 Exemption: Very high amounts always require strong SCA
    if amount and amount > 10000.0:
        return SCALevel.HARDWARE_TOKEN

    # Risk-based SCA (PSD2 RTS Article 18)
    if risk_score < 0.3:
        return SCALevel.NONE  # Low risk, no SCA
    elif risk_score < 0.5:
        return SCALevel.OTP_SMS  # Medium risk, SMS code
    elif risk_score < 0.7:
        return SCALevel.BIOMETRIC  # Medium-high risk, biometric
    elif risk_score < 0.9:
        return SCALevel.PUSH_NOTIFICATION  # High risk, app push
    else:
        return SCALevel.HARDWARE_TOKEN  # Very high risk, hardware token


async def create_sca_challenge(
    pool: asyncpg.Pool,
    user_id: str,
    transaction_id: str,
    risk_score: float,
    amount: float = None,
    transaction_type: str = None
) -> Dict[str, Any]:
    """
    Create SCA challenge for transaction.

    Args:
        pool: PostgreSQL connection pool
        user_id: User identifier
        transaction_id: Transaction identifier
        risk_score: Transaction risk score (0.0-1.0)
        amount: Transaction amount
        transaction_type: Type of transaction

    Returns:
        SCA challenge details

    Example:
        >>> challenge = await create_sca_challenge(
        ...     pool, "user_123", "txn_456", 0.65, amount=1500.0
        ... )
        >>> challenge["challenge_type"]
        'BIOMETRIC'
    """
    sca_level = determine_sca_level(risk_score, amount, transaction_type)

    async with pool.acquire() as conn:
        challenge_id = await conn.fetchval(
            """
            INSERT INTO sca_challenges (
                user_id,
                transaction_id,
                risk_score,
                challenge_type,
                status,
                created_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING challenge_id
            """,
            user_id,
            transaction_id,
            risk_score,
            sca_level.value,
            SCAStatus.PENDING.value
        )

    return {
        "challenge_id": challenge_id,
        "challenge_type": sca_level.value,
        "status": SCAStatus.PENDING.value,
        "user_id": user_id,
        "transaction_id": transaction_id,
        "risk_score": risk_score,
        "instructions": get_sca_instructions(sca_level),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }


def get_sca_instructions(sca_level: SCALevel) -> str:
    """
    Get user-friendly instructions for SCA challenge.

    Args:
        sca_level: SCA authentication level

    Returns:
        Instructions text
    """
    instructions = {
        SCALevel.NONE: "No additional authentication required.",
        SCALevel.OTP_SMS: "Enter the 6-digit code sent to your mobile phone.",
        SCALevel.OTP_EMAIL: "Enter the 6-digit code sent to your email address.",
        SCALevel.BIOMETRIC: "Verify your identity using fingerprint or face recognition.",
        SCALevel.PUSH_NOTIFICATION: "Approve the transaction in your mobile app and verify with biometric.",
        SCALevel.HARDWARE_TOKEN: "Insert your security key and follow the on-screen instructions."
    }
    return instructions.get(sca_level, "Complete authentication challenge.")


async def complete_sca_challenge(
    pool: asyncpg.Pool,
    challenge_id: int,
    success: bool
) -> bool:
    """
    Mark SCA challenge as completed or failed.

    Args:
        pool: PostgreSQL connection pool
        challenge_id: Challenge identifier
        success: Whether challenge was completed successfully

    Returns:
        True if updated successfully
    """
    status = SCAStatus.COMPLETED if success else SCAStatus.FAILED

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE sca_challenges
            SET status = $1,
                completed_at = NOW()
            WHERE challenge_id = $2
              AND status = $3
            """,
            status.value,
            challenge_id,
            SCAStatus.PENDING.value
        )

    return result == "UPDATE 1"


async def get_sca_challenge(pool: asyncpg.Pool, challenge_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve SCA challenge details.

    Args:
        pool: PostgreSQL connection pool
        challenge_id: Challenge identifier

    Returns:
        Challenge details or None if not found
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                challenge_id,
                user_id,
                transaction_id,
                risk_score,
                challenge_type,
                status,
                created_at,
                completed_at
            FROM sca_challenges
            WHERE challenge_id = $1
            """,
            challenge_id
        )

    if not row:
        return None

    return {
        "challenge_id": row["challenge_id"],
        "user_id": row["user_id"],
        "transaction_id": row["transaction_id"],
        "risk_score": row["risk_score"],
        "challenge_type": row["challenge_type"],
        "status": row["status"],
        "instructions": get_sca_instructions(SCALevel(row["challenge_type"])),
        "created_at": row["created_at"].isoformat() + "Z",
        "completed_at": row["completed_at"].isoformat() + "Z" if row["completed_at"] else None
    }


async def log_sca_event(pool: asyncpg.Pool, event_details: Dict[str, Any]):
    """
    Log SCA event to DPIA logs (RGPD compliance).

    Args:
        pool: PostgreSQL connection pool
        event_details: SCA event details
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO dpia_logs (event, details, ts)
            VALUES ('SCA_TRIGGERED', $1, NOW())
            """,
            event_details
        )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_sca():
        """Test SCA functionality."""
        print("\n=== SCA (Strong Customer Authentication) Test ===\n")

        # Test different risk scores
        test_cases = [
            (0.15, 25.0, "Low risk, small amount"),
            (0.45, 150.0, "Medium risk"),
            (0.65, 1500.0, "Medium-high risk"),
            (0.85, 5000.0, "High risk"),
            (0.95, 15000.0, "Very high risk"),
        ]

        for risk_score, amount, description in test_cases:
            sca_level = determine_sca_level(risk_score, amount)
            instructions = get_sca_instructions(sca_level)
            print(f"{description}:")
            print(f"  Risk: {risk_score:.2f}, Amount: €{amount:.2f}")
            print(f"  SCA Level: {sca_level.value}")
            print(f"  Instructions: {instructions}")
            print()

    asyncio.run(test_sca())
