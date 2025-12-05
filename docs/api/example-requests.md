# Exemples de requêtes API

## 1. Transaction ALLOW (légitime)

### Requête
```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGc..." \
  -d @- <<'JSON'
{
  "tenant_id": "bank-fr-001",
  "idempotency_key": "tx-20250930-abc123-001",
  "event": {
    "type": "card_payment",
    "id": "evt_4f8a9c2b1d3e",
    "ts": "2025-09-30T14:23:45.123Z",
    "amount": 45.50,
    "currency": "EUR",
    "merchant": {
      "id": "merch_supermarket_paris_01",
      "name": "Carrefour Paris 15",
      "mcc": "5411",
      "country": "FR"
    },
    "card": {
      "card_id": "card_tok_8f2b3c4d5e6f",
      "type": "physical",
      "user_id": "user_alice_123"
    },
    "context": {
      "ip": "82.64.123.45",
      "geo": "FR",
      "device_id": "dev_iphone_alice_001",
      "channel": "pos"
    },
    "security": {
      "auth_method": "pin",
      "aml_flag": false
    },
    "kyc": {
      "status": "verified",
      "level": "standard",
      "confidence": 0.95
    }
  }
}
JSON
```

### Réponse (200 OK)
```json
{
  "decision_id": "dec_9a8b7c6d5e4f3",
  "decision": "ALLOW",
  "score": 0.08,
  "rule_hits": [],
  "reasons": [],
  "latency_ms": 47,
  "model_version": "gbdt_v1.2.3",
  "sla": {
    "p95_budget_ms": 100
  }
}
```

**Analyse**:
- Montant faible (45.50€)
- Pays cohérent (user FR, merchant FR)
- PIN validé
- KYC vérifié
- Score ML très faible (0.08 = 8% risque)
- ✅ **Décision**: ALLOW

---

## 2. Transaction CHALLENGE (suspecte)

### Requête
```json
{
  "tenant_id": "bank-fr-001",
  "idempotency_key": "tx-20250930-xyz789-002",
  "event": {
    "type": "card_payment",
    "id": "evt_1a2b3c4d5e6f",
    "ts": "2025-09-30T03:42:18.456Z",
    "amount": 899.00,
    "currency": "EUR",
    "merchant": {
      "id": "merch_electronics_de_99",
      "name": "ElectroShop Berlin",
      "mcc": "5732",
      "country": "DE"
    },
    "card": {
      "card_id": "card_tok_8f2b3c4d5e6f",
      "type": "virtual",
      "user_id": "user_alice_123"
    },
    "context": {
      "ip": "185.220.101.42",
      "geo": "DE",
      "device_id": "dev_unknown_browser_001",
      "channel": "web"
    },
    "security": {
      "auth_method": "none",
      "aml_flag": false
    },
    "kyc": {
      "status": "verified",
      "level": "standard",
      "confidence": 0.95
    }
  }
}
```

### Réponse (200 OK)
```json
{
  "decision_id": "dec_f1e2d3c4b5a6",
  "decision": "CHALLENGE",
  "score": 0.62,
  "rule_hits": [
    "rule_night_tx_high_amount",
    "rule_new_device",
    "rule_geo_mismatch"
  ],
  "reasons": [
    "Transaction nocturne inhabituelle (03h42)",
    "Nouveau device non reconnu",
    "Pays différent de l'historique (DE vs FR)",
    "Montant élevé (899€)",
    "Score ML modéré (62%)"
  ],
  "latency_ms": 68,
  "model_version": "gbdt_v1.2.3",
  "sla": {
    "p95_budget_ms": 100
  }
}
```

**Analyse**:
- 🚨 Heure inhabituelle (3h42 du matin)
- 🚨 Nouveau device jamais vu
- 🚨 Pays différent (user FR habituel → achat DE)
- 🚨 Montant élevé (899€ électronique)
- 🚨 Pas d'authentification forte (3DS manquant)
- Score ML modéré (0.62 = 62% risque)
- ⚠️ **Décision**: CHALLENGE → SMS 2FA / App notification

---

## 3. Transaction DENY (fraude probable)

### Requête
```json
{
  "tenant_id": "bank-fr-001",
  "idempotency_key": "tx-20250930-danger-003",
  "event": {
    "type": "card_payment",
    "id": "evt_dead1234beef",
    "ts": "2025-09-30T12:05:33.789Z",
    "amount": 2499.99,
    "currency": "USD",
    "merchant": {
      "id": "merch_crypto_exchange_ru",
      "name": "CryptoBuy Russia",
      "mcc": "6211",
      "country": "RU"
    },
    "card": {
      "card_id": "card_tok_8f2b3c4d5e6f",
      "type": "physical",
      "user_id": "user_alice_123"
    },
    "context": {
      "ip": "5.188.10.123",
      "geo": "RU",
      "device_id": "dev_tor_browser_999",
      "channel": "web"
    },
    "security": {
      "auth_method": "none",
      "aml_flag": true
    },
    "kyc": {
      "status": "verified",
      "level": "standard",
      "confidence": 0.95
    }
  }
}
```

### Réponse (200 OK)
```json
{
  "decision_id": "dec_critical_001",
  "decision": "DENY",
  "score": 0.94,
  "rule_hits": [
    "rule_deny_crypto_high_risk_country",
    "rule_deny_tor_vpn",
    "rule_velocity_exceeded",
    "rule_aml_flag_critical"
  ],
  "reasons": [
    "Marchand crypto dans pays à haut risque (RU)",
    "Connexion via TOR/VPN détectée",
    "3 transactions en 5 minutes (vélocité anormale)",
    "Flag AML critique activé",
    "Score ML très élevé (94%)",
    "Montant suspect (2499.99 USD = pattern fractionné)"
  ],
  "latency_ms": 52,
  "model_version": "gbdt_v1.2.3",
  "sla": {
    "p95_budget_ms": 100
  }
}
```

**Analyse**:
- 🔴 Crypto exchange (MCC 6211 = haut risque)
- 🔴 Pays sanctionné/haut risque (RU)
- 🔴 TOR/VPN détecté (IP 5.188.x.x = datacenter russe)
- 🔴 AML flag externe (signalement tiers)
- 🔴 Vélocité : 3 tx en 5 min (user Alice normalement 1-2/jour)
- 🔴 Montant juste sous seuil reporting (2500 USD)
- Score ML critique (0.94 = 94% fraude)
- ❌ **Décision**: DENY → Blocage immédiat + case analyste

---

## 4. Retry idempotent (même clé)

### Requête 1 (originale)
```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "bank-fr-001", "idempotency_key": "tx-retry-test-001", ...}'
```

### Réponse 1
```json
{
  "decision_id": "dec_aabbccdd",
  "decision": "ALLOW",
  "latency_ms": 65
}
```

### Requête 2 (retry après 5 secondes, MÊME idempotency_key)
```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "bank-fr-001", "idempotency_key": "tx-retry-test-001", ...}'
```

### Réponse 2 (cache Redis)
```json
{
  "decision_id": "dec_aabbccdd",
  "decision": "ALLOW",
  "latency_ms": 3
}
```

**Note**: 
- Même `decision_id` (idempotence garantie)
- Latence 3ms (cache Redis, pas de retraitement)
- ✅ Pas de double scoring, pas de double facturation

---

## 5. Vélocité excessive (3 transactions en 2 minutes)

### Transaction 1 (t=0s)
```json
{
  "event": {
    "id": "evt_seq_001",
    "ts": "2025-09-30T15:00:00.000Z",
    "amount": 150.00,
    "card": {"card_id": "card_bob_456"}
  }
}
```
**Réponse**: `ALLOW` (vélocité normale)

### Transaction 2 (t=30s)
```json
{
  "event": {
    "id": "evt_seq_002",
    "ts": "2025-09-30T15:00:30.000Z",
    "amount": 220.00,
    "card": {"card_id": "card_bob_456"}
  }
}
```
**Réponse**: `ALLOW` (2 tx en 1 min = acceptable)

### Transaction 3 (t=90s)
```json
{
  "event": {
    "id": "evt_seq_003",
    "ts": "2025-09-30T15:01:30.000Z",
    "amount": 180.00,
    "card": {"card_id": "card_bob_456"}
  }
}
```
**Réponse**: 
```json
{
  "decision": "CHALLENGE",
  "rule_hits": ["rule_velocity_3_tx_per_5min"],
  "reasons": ["3 transactions en 2 minutes (seuil: 2 max)"]
}
```

---

## 6. Nouveau device + montant élevé

### Requête
```json
{
  "tenant_id": "bank-uk-002",
  "idempotency_key": "tx-uk-newdev-004",
  "event": {
    "type": "card_payment",
    "id": "evt_newdevice_001",
    "ts": "2025-09-30T18:30:00.000Z",
    "amount": 1250.00,
    "currency": "GBP",
    "merchant": {
      "id": "merch_jewelry_london",
      "name": "Tiffany & Co London",
      "mcc": "5944",
      "country": "GB"
    },
    "card": {
      "card_id": "card_tok_charlie_789",
      "type": "virtual",
      "user_id": "user_charlie_uk"
    },
    "context": {
      "ip": "81.2.69.142",
      "geo": "GB",
      "device_id": "dev_android_samsung_new_999",
      "channel": "app"
    },
    "security": {
      "auth_method": "biometric",
      "aml_flag": false
    },
    "kyc": {
      "status": "verified",
      "level": "enhanced",
      "confidence": 0.98
    }
  }
}
```

### Réponse
```json
{
  "decision": "CHALLENGE",
  "score": 0.45,
  "rule_hits": ["rule_new_device_high_amount"],
  "reasons": [
    "Premier achat depuis ce device (Samsung Galaxy S24)",
    "Montant élevé pour premier achat (1250 GBP)",
    "Catégorie joaillerie (risque revente)"
  ],
  "latency_ms": 58
}
```

**Note**: Malgré biométrie + KYC enhanced, le nouveau device déclenche CHALLENGE (demande confirmation push app).

---

## 7. Transaction légitime après voyage

### Requête
```json
{
  "tenant_id": "bank-fr-001",
  "idempotency_key": "tx-travel-japan-005",
  "event": {
    "type": "card_payment",
    "id": "evt_travel_jp_001",
    "ts": "2025-09-30T06:15:22.000Z",
    "amount": 8500.00,
    "currency": "JPY",
    "merchant": {
      "id": "merch_hotel_tokyo",
      "name": "Park Hyatt Tokyo",
      "mcc": "7011",
      "country": "JP"
    },
    "card": {
      "card_id": "card_tok_david_321",
      "type": "physical",
      "user_id": "user_david_fr"
    },
    "context": {
      "ip": "210.150.123.89",
      "geo": "JP",
      "device_id": "dev_iphone_david_001",
      "channel": "pos"
    },
    "security": {
      "auth_method": "nfc",
      "aml_flag": false
    },
    "kyc": {
      "status": "verified",
      "level": "standard",
      "confidence": 0.96
    }
  }
}
```

### Réponse
```json
{
  "decision": "ALLOW",
  "score": 0.18,
  "rule_hits": [],
  "reasons": [
    "Notification voyage reçue 2 jours avant (JP 28/09-05/10)",
    "Hôtel légitime (chaîne internationale)",
    "Device reconnu (iPhone habituel)",
    "Paiement NFC cohérent avec POS physique"
  ],
  "latency_ms": 51
}
```

**Note**: User a notifié son voyage via app banking 2 jours avant → whitelist temporaire pays JP.

---

## Structure complète d'un événement (tous champs)

```typescript
interface ScoreRequest {
  tenant_id: string;           // "bank-fr-001"
  idempotency_key: string;     // "tx-{date}-{random}-{seq}"
  event: TransactionEvent;
}

interface TransactionEvent {
  // Identification
  type: "card_payment";
  id: string;                  // Unique tx ID
  ts: string;                  // ISO 8601 timestamp
  
  // Montant
  amount: number;              // 150.50
  currency: string;            // "EUR" (ISO 4217)
  
  // Marchand
  merchant: {
    id: string;                // Internal merchant ID
    name?: string;             // "Carrefour Paris 15"
    mcc: string;               // "5411" (4 digits)
    country: string;           // "FR" (ISO 3166-1)
  };
  
  // Carte
  card: {
    card_id: string;           // Tokenized (jamais PAN)
    type: "physical" | "virtual";
    user_id: string;           // User identifier
  };
  
  // Contexte
  context: {
    ip?: string;               // "82.64.123.45"
    geo?: string;              // "FR" (country from IP)
    device_id?: string;        // Fingerprint
    channel: "app" | "web" | "pos" | "atm";
  };
  
  // Sécurité (optionnel)
  security?: {
    auth_method?: "3ds" | "pin" | "biometric" | "nfc" | "none";
    aml_flag?: boolean;        // Flag externe
  };
  
  // KYC (optionnel)
  kyc?: {
    status?: "verified" | "pending" | "unverified";
    level?: "basic" | "standard" | "enhanced";
    confidence?: number;       // 0.0 to 1.0
  };
}

interface ScoreResponse {
  decision_id: string;         // Unique audit ID
  decision: "ALLOW" | "CHALLENGE" | "DENY";
  score?: number;              // 0.0 to 1.0 (ML score)
  rule_hits: string[];         // ["rule_id_1", ...]
  reasons: string[];           // Human-readable
  latency_ms: number;          // Processing time
  model_version: string;       // "gbdt_v1.2.3"
  sla?: {
    p95_budget_ms: number;     // 100
  };
}
```

---

## Codes d'erreur

### 400 Bad Request
```json
{
  "error": "validation_error",
  "details": [
    {
      "field": "event.amount",
      "message": "must be greater than 0"
    }
  ]
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "retry_after_seconds": 60,
  "limit": "100 requests per minute"
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "error_id": "err_9f8e7d6c5b4a",
  "message": "An error occurred. Contact support with error_id."
}
```

### 503 Service Unavailable
```json
{
  "error": "service_unavailable",
  "message": "Model serving timeout",
  "fallback_used": "rules_only"
}
```
