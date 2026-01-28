#!/usr/bin/env python3
"""Test de l'endpoint send-frauds : envoi de transactions au Decision Engine."""
import json
import sys

try:
    import httpx
except ImportError:
    print("Installation requise: pip install httpx")
    sys.exit(1)

GENERATOR_URL = "http://localhost:8010"
SEND_FRAUDS_PATH = "/v1/generator/send-frauds"


def main():
    print("Test send-frauds -> Decision Engine")
    print(f"  Générateur: {GENERATOR_URL}")
    print()

    payload = {
        "count": 10,
        "fraud_ratio": 0.3,
        "currency": "EUR",
        "countries": ["FR"],
        "seed": 42,
    }

    try:
        resp = httpx.post(
            f"{GENERATOR_URL}{SEND_FRAUDS_PATH}",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        print("Réponse OK (200)")
        print(json.dumps(data, indent=2, default=str))
        print()
        print(f"  Générées: {data.get('generated', 0)}")
        print(f"  Envoyées au Decision Engine: {data.get('sent', 0)}")
        print(f"  Échecs: {data.get('failed', 0)}")
        print(f"  Latence: {data.get('latency_ms', 0)} ms")
        if data.get("decisions_summary"):
            print("  Décisions:", data["decisions_summary"])
        if data.get("failed", 0) > 0 and data.get("sent", 0) == 0:
            print("\n  -> Le Decision Engine ne répond peut-être pas (vérifier http://localhost:8000).")
        return 0
    except httpx.ConnectError as e:
        print(f"Erreur: impossible de joindre le générateur à {GENERATOR_URL}")
        print("  Démarrez le générateur: uvicorn app.main:app --host 0.0.0.0 --port 8010")
        return 1
    except httpx.HTTPStatusError as e:
        print(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
        return 1
    except Exception as e:
        print(f"Erreur: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
