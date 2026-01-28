"""Tests du flux send-frauds (conversion Transaction -> Decision Engine)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.transaction import Transaction, TransactionType, FraudScenario
from app.services.decision_engine_service import (
    _transaction_to_score_payload,
    decision_engine_service,
)


def test_transaction_to_score_payload():
    """La conversion Transaction -> payload /v1/score doit produire les champs requis."""
    tx = Transaction(
        transaction_id="tx_123",
        user_id="user_456",
        merchant_id="merch_789",
        amount=50.99,
        currency="EUR",
        timestamp=datetime.now(),
        country="FR",
        ip_address="192.168.1.1",
        device_id="dev_1",
        is_fraud=False,
    )
    payload = _transaction_to_score_payload(tx)
    assert payload["event_id"] == "tx_123"
    assert payload["tenant_id"] == "default"
    assert payload["amount"] == 50.99
    assert payload["currency"] == "EUR"
    assert payload["merchant"]["id"] == "merch_789"
    assert payload["merchant"]["country"] == "FR"
    assert payload["merchant"]["mcc"] == "5411"
    assert payload["card"]["user_id"] == "user_456"
    assert payload["card"]["card_id"] == "card_tok_user_456"
    assert payload["context"]["channel"] == "web"
    assert payload["context"]["ip"] == "192.168.1.1"
    assert payload["context"]["geo"] == "FR"
    assert "has_initial_2fa" in payload


def test_transaction_to_score_payload_minimal():
    """Transaction minimale (sans merchant_id, ip) doit quand même produire un payload valide."""
    tx = Transaction(
        transaction_id="tx_min",
        user_id="u1",
        amount=1.0,
        currency="USD",
        timestamp=datetime.now(),
        country="US",
    )
    payload = _transaction_to_score_payload(tx)
    assert payload["event_id"] == "tx_min"
    assert payload["merchant"]["id"].startswith("merch_")
    assert payload["context"]["ip"] == "192.168.1.1"
    assert payload["context"]["channel"] == "pos"


@pytest.mark.asyncio
async def test_send_transactions_mock_decision_engine():
    """En mockant httpx, send_transactions doit retourner une réponse par transaction."""
    tx1 = Transaction(
        transaction_id="evt_1",
        user_id="u1",
        amount=10.0,
        currency="EUR",
        timestamp=datetime.now(),
        country="FR",
    )
    tx2 = Transaction(
        transaction_id="evt_2",
        user_id="u2",
        amount=20.0,
        currency="EUR",
        timestamp=datetime.now(),
        country="DE",
    )
    fake_response = {
        "event_id": "evt_1",
        "decision_id": "dec_abc",
        "decision": "ALLOW",
        "score": 0.15,
        "latency_ms": 50,
    }

    async def mock_post(*args, **kwargs):
        body = kwargs.get("json", {})
        m = MagicMock()
        m.json.return_value = {
            "event_id": body.get("event_id", ""),
            "decision_id": "dec_mock",
            "decision": "ALLOW",
            "score": 0.2,
            "latency_ms": 30,
        }
        m.raise_for_status = MagicMock()
        return m

    with patch.object(decision_engine_service, "_get_client") as get_client:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=mock_post)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        get_client.return_value = client

        results = await decision_engine_service.send_transactions([tx1, tx2])

    assert len(results) == 2
    assert "error" not in results[0]
    assert results[0].get("event_id") == "evt_1"
    assert results[0].get("decision") == "ALLOW"
    assert "error" not in results[1]
    assert results[1].get("event_id") == "evt_2"
