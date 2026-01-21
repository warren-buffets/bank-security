# Schéma Base de Données - PostgreSQL

## Vue d'ensemble des tables

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   events     │       │  decisions   │       │    cases     │
│              │       │              │       │              │
│ PK: event_id │◄──────┤ FK: event_id │◄──────┤ FK: event_id │
│              │       │              │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
                                                      │
                       ┌──────────────┐              │
                       │    labels    │              │
                       │              │              │
                       │ FK: event_id │◄─────────────┘
                       │              │
                       └──────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    rules     │       │    lists     │       │  audit_logs  │
│              │       │              │       │              │
│ PK: rule_id  │       │ PK: compound │       │ PK: log_id   │
│              │       │              │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
```

## Table: `events`

Stocke tous les événements transactionnels entrants (source de vérité).

```sql
CREATE TABLE events (
    event_id        VARCHAR PRIMARY KEY,        -- Unique transaction ID
    tenant_id       VARCHAR NOT NULL,           -- Multi-tenant isolation
    ts              TIMESTAMPTZ NOT NULL,       -- Transaction timestamp
    type            VARCHAR NOT NULL,           -- 'card_payment', 'withdrawal', etc.
    payload_json    JSONB NOT NULL,            -- Full event payload
    idem_key        VARCHAR NOT NULL,           -- Idempotency key (24h TTL)
    hash            BYTEA NOT NULL,             -- SHA256 hash for integrity
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_tenant_ts ON events(tenant_id, ts DESC);
CREATE INDEX idx_events_idem_key ON events(idem_key);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- Payload structure (JSONB):
-- {
--   "amount": 150.00,
--   "currency": "EUR",
--   "merchant": {"id": "...", "mcc": "5411", "country": "FR"},
--   "card": {"card_id": "...", "user_id": "...", "type": "physical"},
--   "context": {"ip": "...", "geo": "FR", "device_id": "...", "channel": "app"}
-- }
```

**Volumétrie estimée**: ~10M rows/jour @ 10k TPS  
**Rétention**: 90 jours online, archive vers data lake après  
**Partitioning**: Par mois (tenant_id, ts)

---

## Table: `decisions`

Stocke les décisions de fraude (immutable, audit trail).

```sql
CREATE TABLE decisions (
    decision_id     VARCHAR PRIMARY KEY,                    -- Unique decision ID
    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
    tenant_id       VARCHAR NOT NULL,
    decision        VARCHAR NOT NULL CHECK(decision IN ('ALLOW','CHALLENGE','DENY')),
    score           NUMERIC(5,4),                          -- ML score [0..1]
    rule_hits       TEXT[] NOT NULL DEFAULT '{}',          -- Array of rule IDs triggered
    reasons         TEXT[] NOT NULL DEFAULT '{}',          -- Human-readable reasons
    thresholds      JSONB,                                 -- Decision thresholds used
    latency_ms      INTEGER NOT NULL,                      -- Processing time
    model_version   VARCHAR NOT NULL,                      -- ML model version
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_decisions_event_id ON decisions(event_id);
CREATE INDEX idx_decisions_tenant_decision ON decisions(tenant_id, decision);
CREATE INDEX idx_decisions_created_at ON decisions(created_at DESC);
CREATE INDEX idx_decisions_score ON decisions(score DESC) WHERE score IS NOT NULL;

-- Immutability trigger
CREATE OR REPLACE FUNCTION prevent_decision_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Decisions are immutable. Create a new decision instead.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_immutable_decisions
BEFORE UPDATE ON decisions
FOR EACH ROW EXECUTE FUNCTION prevent_decision_update();
```

**Volumétrie**: ~10M rows/jour  
**Rétention**: 2 ans (compliance)

---

## Table: `rules` (versionnée, legacy)

Stocke les règles de détection (versionnées, utilisée pour l'historique).

```sql
CREATE TABLE rules (
    rule_id         VARCHAR NOT NULL,
    version         INTEGER NOT NULL,
    dsl             TEXT NOT NULL,                         -- Rule DSL expression
    status          VARCHAR NOT NULL CHECK(status IN ('draft','published','disabled')),
    priority        INTEGER DEFAULT 0,                     -- Execution order
    description     TEXT,
    created_by      VARCHAR NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (rule_id, version)
);

-- Index
CREATE INDEX idx_rules_status ON rules(status) WHERE status = 'published';
```

---

## Table: `rules_v2` (active, utilisée par rules-service)

Table principale des règles utilisée par le rules-service.

```sql
CREATE TABLE rules_v2 (
    id              VARCHAR PRIMARY KEY,                   -- Unique rule identifier
    name            VARCHAR NOT NULL,                      -- Human-readable name
    expression      TEXT NOT NULL,                         -- Rule expression in DSL
    action          VARCHAR NOT NULL CHECK(action IN ('allow', 'deny', 'review', 'challenge')),
    priority        INTEGER DEFAULT 0,                     -- Execution order (higher = first)
    enabled         BOOLEAN DEFAULT true,                  -- Whether rule is active
    description     TEXT,
    metadata        JSONB DEFAULT '{}',                    -- Additional metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX idx_rules_v2_enabled_priority ON rules_v2(enabled, priority DESC);

-- Example expressions:
-- "amount > 5000"
-- "velocity_1h > 10"
-- "card_country != merchant_country"
-- "mcc IN ('7995', '7801')"
```

### Règles par défaut

| ID | Nom | Expression | Action | Priorité |
|----|-----|------------|--------|----------|
| rule_very_high_amount | Very High Amount | `amount > 10000` | deny | 110 |
| rule_high_amount | High Amount | `amount > 5000` | review | 100 |
| rule_extreme_velocity | Extreme Velocity | `velocity_1h > 10` | deny | 95 |
| rule_night_transaction | Night Transaction | `hour >= 0 AND hour <= 5` | review | 90 |
| rule_high_velocity | High Velocity | `velocity_1h > 5` | review | 85 |
| rule_high_risk_country | High Risk Country | `merchant_country IN ('NG', 'RU', 'CN', 'BR')` | review | 78 |
| rule_cross_border | Cross Border | `card_country != merchant_country` | review | 75 |
| rule_crypto | Crypto Purchase | `mcc = '6051' AND amount > 1000` | review | 68 |
| rule_gambling | Gambling | `mcc IN ('7995', '7801', '7802')` | review | 65 |
| rule_vpn_detected | VPN/Proxy | `proxy_vpn_flag = true AND amount > 500` | review | 58 |
| rule_new_device | New Device | `device_age_days < 1` | review | 55 |

**Volumétrie**: ~100-500 rules actives

---

## Table: `lists`

Stocke les listes d'allow/deny (IP, devices, merchants, etc.).

```sql
CREATE TABLE lists (
    list_id         VARCHAR NOT NULL,                      -- 'deny_ip', 'allow_merchant', etc.
    type            VARCHAR NOT NULL CHECK(type IN ('allow','deny','monitor')),
    value           VARCHAR NOT NULL,                      -- IP, device_id, merchant_id, etc.
    metadata        JSONB,                                 -- {"reason": "...", "expires_at": "..."}
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (list_id, value)
);

-- Index
CREATE INDEX idx_lists_type_value ON lists(type, value);
CREATE INDEX idx_lists_metadata ON lists USING GIN(metadata);
```

**Volumétrie**: ~1M entries (deny IPs, devices)  
**Cache**: Redis hot cache (TTL 1h)

---

## Table: `cases`

Stocke les cas de fraude pour investigation manuelle.

```sql
CREATE TABLE cases (
    case_id         VARCHAR PRIMARY KEY,
    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
    queue           VARCHAR NOT NULL,                      -- 'high_risk', 'medium_risk', 'review'
    status          VARCHAR NOT NULL CHECK(status IN ('open','in_progress','closed')),
    assignee        VARCHAR,                               -- Analyst user ID
    priority        INTEGER NOT NULL DEFAULT 0,           -- 0=low, 1=medium, 2=high
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    resolution      VARCHAR                                -- 'fraud_confirmed', 'false_positive', etc.
);

-- Indexes
CREATE INDEX idx_cases_queue_status ON cases(queue, status);
CREATE INDEX idx_cases_assignee ON cases(assignee) WHERE status != 'closed';
CREATE INDEX idx_cases_priority ON cases(priority DESC);
```

**Volumétrie**: ~1-5% des transactions (CHALLENGE/DENY)

---

## Table: `labels`

Stocke les labels de vérité terrain (feedback loop pour ML).

```sql
CREATE TABLE labels (
    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
    label           VARCHAR NOT NULL CHECK(label IN ('fraud','legit','chargeback','fp')),
    source          VARCHAR NOT NULL,                      -- 'analyst', 'customer', 'chargeback_system'
    confidence      NUMERIC(3,2),                          -- 0.0 to 1.0
    ts              TIMESTAMPTZ NOT NULL,
    metadata        JSONB,
    PRIMARY KEY (event_id, label, source)
);

-- Index
CREATE INDEX idx_labels_event_id ON labels(event_id);
CREATE INDEX idx_labels_label ON labels(label);
```

**Usage**: Retraining pipeline, backtesting

---

## Table: `audit_logs`

Stocke tous les changements critiques (immutable, signé).

```sql
CREATE TABLE audit_logs (
    log_id          BIGSERIAL PRIMARY KEY,
    actor           VARCHAR NOT NULL,                      -- User/Service who made change
    action          VARCHAR NOT NULL,                      -- 'CREATE', 'UPDATE', 'DELETE'
    entity          VARCHAR NOT NULL,                      -- Table name
    entity_id       VARCHAR NOT NULL,                      -- Primary key of entity
    before          JSONB,                                 -- State before change
    after           JSONB,                                 -- State after change
    ts              TIMESTAMPTZ DEFAULT NOW(),
    signature       BYTEA NOT NULL,                        -- HMAC-SHA256 signature
    prev_log_hash   BYTEA                                  -- Hash of previous log (chain)
);

-- Index
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity, entity_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_ts ON audit_logs(ts DESC);
```

**Rétention**: 7 ans (compliance)  
**WORM**: Write-Once-Read-Many via trigger

---

## Contraintes et invariants

### Référentielle
- `decisions.event_id` → `events.event_id` (CASCADE on DELETE)
- `cases.event_id` → `events.event_id`
- `labels.event_id` → `events.event_id`

### Immutabilité
- `decisions`: BEFORE UPDATE trigger → RAISE EXCEPTION
- `audit_logs`: BEFORE UPDATE/DELETE trigger → RAISE EXCEPTION

### Checksums
- `events.hash`: SHA256(event_id + tenant_id + ts + payload_json)
- Vérifié à l'insertion et lors des audits

---

## Volumétrie et sizing

### À 10k TPS (864M tx/jour)

| Table       | Rows/jour | Taille/jour | Rétention | Total      |
|-------------|-----------|-------------|-----------|------------|
| events      | 10M       | ~5 GB       | 90 jours  | 450 GB     |
| decisions   | 10M       | ~3 GB       | 2 ans     | 2.2 TB     |
| cases       | 500k      | ~200 MB     | 1 an      | 73 GB      |
| labels      | 1M        | ~100 MB     | Permanent | Croissant  |
| rules       | ~10       | ~1 MB       | Permanent | Négligeable|
| lists       | Variable  | ~50 MB      | Dynamic   | ~500 MB    |
| audit_logs  | 100k      | ~50 MB      | 7 ans     | 128 GB     |

**Total estimé**: ~3 TB sur 2 ans

### Optimisations recommandées
- Partitioning par mois sur `events`, `decisions`
- Indexes partiels sur colonnes à forte cardinalité
- Archivage automatique vers S3/MinIO (cold storage)
- Compression TOAST sur colonnes JSONB

---

## Scripts de migration

### V001__init.sql
Création des tables principales (events, decisions, rules, lists, cases, labels, audit_logs)

### V002__indices.sql
Création des index de performance

### V003__triggers.sql
Triggers d'immutabilité et audit (prevent_decision_update, etc.)

### V004__seed_data.sql
Données de test initiales

### V005__rules_service_compat.sql
- Création de la table `rules_v2` compatible avec rules-service
- Vue `rules_active` pour mapping legacy
- Seed des 11 règles de détection par défaut
- Trigger `updated_at` automatique
