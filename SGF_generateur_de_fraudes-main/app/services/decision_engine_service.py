"""Service pour envoyer les transactions générées vers le Decision Engine (SafeGuard)."""
import logging
from typing import List, Dict, Any, Optional

import httpx
from app.config import settings
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _transaction_to_score_payload(tx: Transaction, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Convertit une Transaction (générateur) en corps de requête POST /v1/score (decision-engine)."""
    tenant_id = tenant_id or settings.decision_engine_tenant_id
    # Merchant: id, mcc (4 digits), country requis
    merchant_id = tx.merchant_id or f"merch_{tx.user_id[:8]}"
    mcc = "5411"  # Grocery default, decision-engine attend 4 chiffres
    # Card: card_id, user_id, type
    card_id = f"card_tok_{tx.user_id}"
    card_type = "virtual" if (tx.ip_address and tx.device_id) else "physical"
    # Context: channel, ip, geo, device_id
    channel = "web" if tx.ip_address else "pos"
    ip = tx.ip_address or "192.168.1.1"
    geo = tx.country
    return {
        "event_id": tx.transaction_id,
        "tenant_id": tenant_id,
        "amount": round(tx.amount, 2),
        "currency": tx.currency,
        "merchant": {
            "id": merchant_id,
            "name": f"Merchant {merchant_id}",
            "mcc": mcc,
            "country": tx.country,
        },
        "card": {
            "card_id": card_id,
            "user_id": tx.user_id,
            "type": card_type,
            "bin": tx.card_last4,
        },
        "context": {
            "channel": channel,
            "ip": ip,
            "geo": geo,
            "device_id": tx.device_id,
            "user_agent": None,
            "proxy_vpn_flag": False,
        },
        "has_initial_2fa": False,
        "metadata": {"generator_batch": tx.batch_id, "is_fraud_label": tx.is_fraud},
    }


class DecisionEngineService:
    """Envoi des transactions vers le Decision Engine SafeGuard."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            base = settings.decision_engine_url.rstrip("/")
            self._client = httpx.AsyncClient(
                base_url=base,
                timeout=settings.decision_engine_timeout_seconds,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def score_transaction(self, tx: Transaction, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Envoie une transaction au Decision Engine et retourne la réponse (score, decision, etc.)."""
        client = await self._get_client()
        payload = _transaction_to_score_payload(tx, tenant_id=tenant_id)
        try:
            resp = await client.post("/v1/score", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning("Decision engine request failed for %s: %s", tx.transaction_id, e)
            raise

    async def send_transactions(
        self,
        transactions: List[Transaction],
        tenant_id: Optional[str] = None,
        stop_on_error: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Envoie une liste de transactions au Decision Engine (POST /v1/score pour chaque).
        Retourne la liste des réponses (une par transaction). En cas d'erreur, l'entrée
        peut être {"error": "..."} si stop_on_error est False.
        """
        results = []
        for tx in transactions:
            try:
                r = await self.score_transaction(tx, tenant_id=tenant_id)
                results.append(r)
            except Exception as e:
                results.append({"error": str(e), "event_id": tx.transaction_id})
                if stop_on_error:
                    raise
        return results


decision_engine_service = DecisionEngineService()
