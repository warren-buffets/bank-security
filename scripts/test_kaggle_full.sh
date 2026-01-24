#!/bin/bash

# Script de test pour vérifier l'intégration des features Kaggle et le cache IP Redis
# Usage: ./scripts/test_kaggle_full.sh

URL="http://localhost:8000/v1/score"
IP_TO_TEST="82.64.1.1" # IP Exemple (France)

echo "🧪 Test de transaction complète (Kaggle Features + IP Cache)"
echo "Target: $URL"
echo "IP: $IP_TO_TEST"
echo "---------------------------------------------------"

# Fonction pour générer le payload JSON
generate_payload() {
  local id=$1
  cat <<EOF
{
  "event_id": "$id",
  "tenant_id": "bank-fr-001",
  "amount": 1250.50,
  "currency": "EUR",
  "merchant": {
    "id": "merch_luxe_paris",
    "name": "Galeries Lafayette",
    "mcc": "5411",
    "country": "FR",
    "lat": 48.8738,
    "long": 2.3320
  },
  "card": {
    "card_id": "card_platinum_01",
    "type": "physical",
    "user_id": "user_vip_01"
  },
  "context": {
    "ip": "$IP_TO_TEST",
    "geo": "FR",
    "device_id": "dev_iphone13",
    "channel": "app",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"
  }
}
EOF
}

echo "1️⃣  Envoi Transaction 1 (Cache Miss attendu)..."
time curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$(generate_payload "tx_test_$(date +%s)_1")" | jq .

echo -e "\n⏳ Pause de 1 seconde...\n"
sleep 1

echo "2️⃣  Envoi Transaction 2 (Même IP -> Cache Hit espéré)..."
time curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$(generate_payload "tx_test_$(date +%s)_2")" | jq .

echo -e "\n---------------------------------------------------"
echo "🔍 Vérification des clés Redis (recherche de *ip*)..."

# Tente de lister les clés via docker si possible
if command -v docker &> /dev/null; then
    echo "> docker exec antifraud-redis redis-cli KEYS \"*ip*\""
    docker exec antifraud-redis redis-cli KEYS "*ip*" 2>/dev/null || echo "⚠️  Impossible de connecter à Redis via Docker automatiquement."
else
    echo "ℹ️  Docker non détecté. Lancez 'make redis-connect' puis 'KEYS *ip*' manuellement."
fi