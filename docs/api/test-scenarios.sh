#!/bin/bash
# Test scenarios for safeguard API

API_URL="${API_URL:-http://localhost:8000}"

echo "🧪 Testing SafeGuard API..."
echo "API URL: $API_URL"
echo ""

# Test 1: Legitimate transaction (ALLOW)
echo "📝 Test 1: Legitimate transaction (should ALLOW)"
curl -s -X POST "$API_URL/v1/score" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "bank-test-001",
    "idempotency_key": "test-allow-001",
    "event": {
      "type": "card_payment",
      "id": "evt_test_001",
      "ts": "2025-09-30T14:00:00Z",
      "amount": 25.50,
      "currency": "EUR",
      "merchant": {
        "id": "merch_cafe_001",
        "name": "Local Cafe",
        "mcc": "5812",
        "country": "FR"
      },
      "card": {
        "card_id": "card_test_001",
        "type": "physical",
        "user_id": "user_test_001"
      },
      "context": {
        "ip": "82.64.1.1",
        "geo": "FR",
        "device_id": "dev_test_001",
        "channel": "pos"
      },
      "security": {
        "auth_method": "pin"
      }
    }
  }' | jq '.'
echo ""

# Test 2: Suspicious transaction (CHALLENGE)
echo "📝 Test 2: Suspicious transaction (should CHALLENGE)"
curl -s -X POST "$API_URL/v1/score" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "bank-test-001",
    "idempotency_key": "test-challenge-002",
    "event": {
      "type": "card_payment",
      "id": "evt_test_002",
      "ts": "2025-09-30T03:30:00Z",
      "amount": 750.00,
      "currency": "EUR",
      "merchant": {
        "id": "merch_electronics_002",
        "name": "Electronics Store",
        "mcc": "5732",
        "country": "DE"
      },
      "card": {
        "card_id": "card_test_001",
        "type": "virtual",
        "user_id": "user_test_001"
      },
      "context": {
        "ip": "185.220.1.1",
        "geo": "DE",
        "device_id": "dev_unknown_999",
        "channel": "web"
      },
      "security": {
        "auth_method": "none"
      }
    }
  }' | jq '.'
echo ""

# Test 3: High-risk transaction (DENY)
echo "📝 Test 3: High-risk transaction (should DENY)"
curl -s -X POST "$API_URL/v1/score" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "bank-test-001",
    "idempotency_key": "test-deny-003",
    "event": {
      "type": "card_payment",
      "id": "evt_test_003",
      "ts": "2025-09-30T12:00:00Z",
      "amount": 2499.99,
      "currency": "USD",
      "merchant": {
        "id": "merch_crypto_999",
        "name": "Crypto Exchange",
        "mcc": "6211",
        "country": "RU"
      },
      "card": {
        "card_id": "card_test_001",
        "type": "physical",
        "user_id": "user_test_001"
      },
      "context": {
        "ip": "5.188.10.1",
        "geo": "RU",
        "device_id": "dev_tor_999",
        "channel": "web"
      },
      "security": {
        "auth_method": "none",
        "aml_flag": true
      }
    }
  }' | jq '.'
echo ""

# Test 4: Idempotency (retry same key)
echo "📝 Test 4: Idempotency test (should return cached response)"
curl -s -X POST "$API_URL/v1/score" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "bank-test-001",
    "idempotency_key": "test-allow-001",
    "event": {
      "type": "card_payment",
      "id": "evt_test_001",
      "ts": "2025-09-30T14:00:00Z",
      "amount": 25.50,
      "currency": "EUR",
      "merchant": {"id": "merch_cafe_001", "mcc": "5812", "country": "FR"},
      "card": {"card_id": "card_test_001", "type": "physical", "user_id": "user_test_001"},
      "context": {"geo": "FR", "channel": "pos"}
    }
  }' | jq '.'
echo ""

echo "✅ Tests completed"
