#!/usr/bin/env python3
"""
Tests du flux send-frauds (sans serveur).
Exécuter depuis la racine du projet : python3 scripts/run_send_frauds_tests.py
Nécessite : pip install pydantic httpx
"""
import sys
import os

# Ajouter la racine du projet au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

def test_conversion():
    """Conversion Transaction -> payload /v1/score."""
    from app.models.transaction import Transaction
    from app.services.decision_engine_service import _transaction_to_score_payload

    tx = Transaction(
        transaction_id="tx_123",
        user_id="user_456",
        amount=50.99,
        currency="EUR",
        timestamp=datetime.now(),
        country="FR",
        ip_address="192.168.1.1",
    )
    payload = _transaction_to_score_payload(tx)
    assert payload["event_id"] == "tx_123"
    assert payload["amount"] == 50.99
    assert payload["merchant"]["country"] == "FR"
    assert payload["card"]["user_id"] == "user_456"
    assert "has_initial_2fa" in payload
    print("  [OK] Conversion Transaction -> ScoreRequest")


def main():
    print("Tests send-frauds (sans serveur)")
    try:
        test_conversion()
        print("\nTous les tests sont passés.")
        return 0
    except ImportError as e:
        print(f"Import manquant: {e}")
        print("  pip install pydantic httpx")
        return 1
    except AssertionError as e:
        print(f"Échec: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
