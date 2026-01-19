# 📋 Guide des Pull Requests - FraudGuard AI

Ce document liste toutes les Pull Requests créées pour le développement de FraudGuard AI.

## 🎯 Pull Requests disponibles

### 1. Database Migrations
**Branch**: `feature/database-migrations`  
**Description**: PR_DATABASE_MIGRATIONS.md  
**Fichiers**: 4 migrations SQL (344 lignes)  
**Status**: ✅ Prêt pour review

M	README.md
diff --git a/platform/postgres/migrations/V001__init.sql b/platform/postgres/migrations/V001__init.sql
new file mode 100644
index 0000000..8ec6410
--- /dev/null
+++ b/platform/postgres/migrations/V001__init.sql
@@ -0,0 +1,180 @@
+-- V001__init.sql
+-- Create all core tables for fraud detection platform
+-- PostgreSQL 14+
+
+-- ============================================================================
+-- Table: events
+-- Stores all incoming transactional events (source of truth)
+-- ============================================================================
+
+CREATE TABLE events (
+    event_id        VARCHAR PRIMARY KEY,
+    tenant_id       VARCHAR NOT NULL,
+    ts              TIMESTAMPTZ NOT NULL,
+    type            VARCHAR NOT NULL,
+    payload_json    JSONB NOT NULL,
+    idem_key        VARCHAR NOT NULL,
+    hash            BYTEA NOT NULL,
+    created_at      TIMESTAMPTZ DEFAULT NOW()
+);
+
+COMMENT ON TABLE events IS 'Stores all incoming transactional events (source of truth)';
+COMMENT ON COLUMN events.event_id IS 'Unique transaction ID';
+COMMENT ON COLUMN events.tenant_id IS 'Multi-tenant isolation';
+COMMENT ON COLUMN events.ts IS 'Transaction timestamp';
+COMMENT ON COLUMN events.type IS 'Event type: card_payment, withdrawal, etc.';
+COMMENT ON COLUMN events.payload_json IS 'Full event payload in JSON format';
+COMMENT ON COLUMN events.idem_key IS 'Idempotency key (24h TTL)';
+COMMENT ON COLUMN events.hash IS 'SHA256 hash for integrity verification';
+
+-- ============================================================================
+-- Table: decisions
+-- Stores fraud decisions (immutable, audit trail)
+-- ============================================================================
+
+CREATE TABLE decisions (
+    decision_id     VARCHAR PRIMARY KEY,
+    event_id        VARCHAR NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
+    tenant_id       VARCHAR NOT NULL,
+    decision        VARCHAR NOT NULL CHECK(decision IN ('ALLOW','CHALLENGE','DENY')),
+    score           NUMERIC(5,4),
+    rule_hits       TEXT[] NOT NULL DEFAULT '{}',
+    reasons         TEXT[] NOT NULL DEFAULT '{}',
+    thresholds      JSONB,
+    latency_ms      INTEGER NOT NULL,
+    model_version   VARCHAR NOT NULL,
+    created_at      TIMESTAMPTZ DEFAULT NOW()
+);
+
+COMMENT ON TABLE decisions IS 'Stores fraud decisions (immutable, audit trail)';
+COMMENT ON COLUMN decisions.decision_id IS 'Unique decision ID';
+COMMENT ON COLUMN decisions.event_id IS 'Reference to events table';
+COMMENT ON COLUMN decisions.decision IS 'Decision outcome: ALLOW, CHALLENGE, or DENY';
+COMMENT ON COLUMN decisions.score IS 'ML fraud score [0..1]';
+COMMENT ON COLUMN decisions.rule_hits IS 'Array of rule IDs that were triggered';
+COMMENT ON COLUMN decisions.reasons IS 'Human-readable reasons for decision';
+COMMENT ON COLUMN decisions.thresholds IS 'Decision thresholds used';
+COMMENT ON COLUMN decisions.latency_ms IS 'Processing time in milliseconds';
+COMMENT ON COLUMN decisions.model_version IS 'ML model version used';
+
+-- ============================================================================
+-- Table: rules
+-- Stores detection rules (versioned)
+-- ============================================================================
+
+CREATE TABLE rules (
+    rule_id         VARCHAR NOT NULL,
+    version         INTEGER NOT NULL,
+    dsl             TEXT NOT NULL,
+    status          VARCHAR NOT NULL CHECK(status IN ('draft','published','disabled')),
+    priority        INTEGER DEFAULT 0,
+    description     TEXT,
+    created_by      VARCHAR NOT NULL,
+    created_at      TIMESTAMPTZ DEFAULT NOW(),
+    PRIMARY KEY (rule_id, version)
+);
+
+COMMENT ON TABLE rules IS 'Stores detection rules (versioned)';
+COMMENT ON COLUMN rules.rule_id IS 'Rule identifier';
+COMMENT ON COLUMN rules.version IS 'Rule version number';
+COMMENT ON COLUMN rules.dsl IS 'Rule DSL expression';
+COMMENT ON COLUMN rules.status IS 'Rule status: draft, published, or disabled';
+COMMENT ON COLUMN rules.priority IS 'Execution order priority';
+COMMENT ON COLUMN rules.created_by IS 'User who created the rule';
+
+-- ============================================================================
+-- Table: lists
+-- Stores allow/deny lists (IP, devices, merchants, etc.)
+-- ============================================================================
+
+CREATE TABLE lists (
+    list_id         VARCHAR NOT NULL,
+    type            VARCHAR NOT NULL CHECK(type IN ('allow','deny','monitor')),
+    value           VARCHAR NOT NULL,
+    metadata        JSONB,
+    created_at      TIMESTAMPTZ DEFAULT NOW(),
+    PRIMARY KEY (list_id, value)
+);
+
+COMMENT ON TABLE lists IS 'Stores allow/deny lists for IPs, devices, merchants, etc.';
+COMMENT ON COLUMN lists.list_id IS 'List identifier (e.g., deny_ip, allow_merchant)';
+COMMENT ON COLUMN lists.type IS 'List type: allow, deny, or monitor';
+COMMENT ON COLUMN lists.value IS 'List value (IP, device_id, merchant_id, etc.)';
+COMMENT ON COLUMN lists.metadata IS 'Additional metadata (reason, expires_at, etc.)';
+
+-- ============================================================================
+-- Table: cases
+-- Stores fraud cases for manual investigation
+-- ============================================================================
+
+CREATE TABLE cases (
+    case_id         VARCHAR PRIMARY KEY,
+    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
+    queue           VARCHAR NOT NULL,
+    status          VARCHAR NOT NULL CHECK(status IN ('open','in_progress','closed')),
+    assignee        VARCHAR,
+    priority        INTEGER NOT NULL DEFAULT 0,
+    notes           TEXT,
+    created_at      TIMESTAMPTZ DEFAULT NOW(),
+    updated_at      TIMESTAMPTZ DEFAULT NOW(),
+    closed_at       TIMESTAMPTZ,
+    resolution      VARCHAR
+);
+
+COMMENT ON TABLE cases IS 'Stores fraud cases for manual investigation';
+COMMENT ON COLUMN cases.case_id IS 'Unique case identifier';
+COMMENT ON COLUMN cases.event_id IS 'Reference to events table';
+COMMENT ON COLUMN cases.queue IS 'Case queue (high_risk, medium_risk, review)';
+COMMENT ON COLUMN cases.status IS 'Case status: open, in_progress, or closed';
+COMMENT ON COLUMN cases.assignee IS 'Analyst user ID';
+COMMENT ON COLUMN cases.priority IS 'Priority: 0=low, 1=medium, 2=high';
+COMMENT ON COLUMN cases.resolution IS 'Final resolution (fraud_confirmed, false_positive, etc.)';
+
+-- ============================================================================
+-- Table: labels
+-- Stores ground truth labels (feedback loop for ML)
+-- ============================================================================
+
+CREATE TABLE labels (
+    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
+    label           VARCHAR NOT NULL CHECK(label IN ('fraud','legit','chargeback','fp')),
+    source          VARCHAR NOT NULL,
+    confidence      NUMERIC(3,2),
+    ts              TIMESTAMPTZ NOT NULL,
+    metadata        JSONB,
+    PRIMARY KEY (event_id, label, source)
+);
+
+COMMENT ON TABLE labels IS 'Stores ground truth labels for ML training';
+COMMENT ON COLUMN labels.event_id IS 'Reference to events table';
+COMMENT ON COLUMN labels.label IS 'Label type: fraud, legit, chargeback, or fp (false positive)';
+COMMENT ON COLUMN labels.source IS 'Label source (analyst, customer, chargeback_system)';
+COMMENT ON COLUMN labels.confidence IS 'Confidence score [0.0 to 1.0]';
+
+-- ============================================================================
+-- Table: audit_logs
+-- Stores all critical changes (immutable, signed)
+-- ============================================================================
+
+CREATE TABLE audit_logs (
+    log_id          BIGSERIAL PRIMARY KEY,
+    actor           VARCHAR NOT NULL,
+    action          VARCHAR NOT NULL,
+    entity          VARCHAR NOT NULL,
+    entity_id       VARCHAR NOT NULL,
+    before          JSONB,
+    after           JSONB,
+    ts              TIMESTAMPTZ DEFAULT NOW(),
+    signature       BYTEA NOT NULL,
+    prev_log_hash   BYTEA
+);
+
+COMMENT ON TABLE audit_logs IS 'Stores all critical changes (immutable, signed)';
+COMMENT ON COLUMN audit_logs.actor IS 'User or service who made the change';
+COMMENT ON COLUMN audit_logs.action IS 'Action type: CREATE, UPDATE, DELETE';
+COMMENT ON COLUMN audit_logs.entity IS 'Table name';
+COMMENT ON COLUMN audit_logs.entity_id IS 'Primary key of the entity';
+COMMENT ON COLUMN audit_logs.before IS 'State before change';
+COMMENT ON COLUMN audit_logs.after IS 'State after change';
+COMMENT ON COLUMN audit_logs.signature IS 'HMAC-SHA256 signature';
+COMMENT ON COLUMN audit_logs.prev_log_hash IS 'Hash of previous log (chain)';
diff --git a/platform/postgres/migrations/V002__indices.sql b/platform/postgres/migrations/V002__indices.sql
new file mode 100644
index 0000000..f71d00d
--- /dev/null
+++ b/platform/postgres/migrations/V002__indices.sql
@@ -0,0 +1,57 @@
+-- V002__indices.sql
+-- Create all performance indexes on tables
+-- PostgreSQL 14+
+
+-- ============================================================================
+-- Indexes for events table
+-- ============================================================================
+
+CREATE INDEX idx_events_tenant_ts ON events(tenant_id, ts DESC);
+CREATE INDEX idx_events_idem_key ON events(idem_key);
+CREATE INDEX idx_events_type ON events(type);
+CREATE INDEX idx_events_created_at ON events(created_at DESC);
+
+-- ============================================================================
+-- Indexes for decisions table
+-- ============================================================================
+
+CREATE INDEX idx_decisions_event_id ON decisions(event_id);
+CREATE INDEX idx_decisions_tenant_decision ON decisions(tenant_id, decision);
+CREATE INDEX idx_decisions_created_at ON decisions(created_at DESC);
+CREATE INDEX idx_decisions_score ON decisions(score DESC) WHERE score IS NOT NULL;
+
+-- ============================================================================
+-- Indexes for rules table
+-- ============================================================================
+
+CREATE INDEX idx_rules_status ON rules(status) WHERE status = 'published';
+
+-- ============================================================================
+-- Indexes for lists table
+-- ============================================================================
+
+CREATE INDEX idx_lists_type_value ON lists(type, value);
+CREATE INDEX idx_lists_metadata ON lists USING GIN(metadata);
+
+-- ============================================================================
+-- Indexes for cases table
+-- ============================================================================
+
+CREATE INDEX idx_cases_queue_status ON cases(queue, status);
+CREATE INDEX idx_cases_assignee ON cases(assignee) WHERE status != 'closed';
+CREATE INDEX idx_cases_priority ON cases(priority DESC);
+
+-- ============================================================================
+-- Indexes for labels table
+-- ============================================================================
+
+CREATE INDEX idx_labels_event_id ON labels(event_id);
+CREATE INDEX idx_labels_label ON labels(label);
+
+-- ============================================================================
+-- Indexes for audit_logs table
+-- ============================================================================
+
+CREATE INDEX idx_audit_logs_entity ON audit_logs(entity, entity_id);
+CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
+CREATE INDEX idx_audit_logs_ts ON audit_logs(ts DESC);
diff --git a/platform/postgres/migrations/V003__triggers.sql b/platform/postgres/migrations/V003__triggers.sql
new file mode 100644
index 0000000..06a03d1
--- /dev/null
+++ b/platform/postgres/migrations/V003__triggers.sql
@@ -0,0 +1,39 @@
+-- V003__triggers.sql
+-- Create immutability triggers for decisions and audit_logs tables
+-- PostgreSQL 14+
+
+-- ============================================================================
+-- Immutability trigger for decisions table
+-- Prevents any updates to decisions once created (audit trail requirement)
+-- ============================================================================
+
+CREATE OR REPLACE FUNCTION prevent_decision_update()
+RETURNS TRIGGER AS $$
+BEGIN
+    RAISE EXCEPTION 'Decisions are immutable. Create a new decision instead.';
+END;
+$$ LANGUAGE plpgsql;
+
+CREATE TRIGGER trigger_immutable_decisions
+BEFORE UPDATE ON decisions
+FOR EACH ROW EXECUTE FUNCTION prevent_decision_update();
+
+-- ============================================================================
+-- Immutability triggers for audit_logs table
+-- Prevents any updates or deletes (WORM - Write Once Read Many)
+-- ============================================================================
+
+CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
+RETURNS TRIGGER AS $$
+BEGIN
+    RAISE EXCEPTION 'Audit logs are immutable. No modifications allowed.';
+END;
+$$ LANGUAGE plpgsql;
+
+CREATE TRIGGER trigger_immutable_audit_logs_update
+BEFORE UPDATE ON audit_logs
+FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
+
+CREATE TRIGGER trigger_immutable_audit_logs_delete
+BEFORE DELETE ON audit_logs
+FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
diff --git a/platform/postgres/migrations/V004__seed_data.sql b/platform/postgres/migrations/V004__seed_data.sql
new file mode 100644
index 0000000..7b07bc1
--- /dev/null
+++ b/platform/postgres/migrations/V004__seed_data.sql
@@ -0,0 +1,68 @@
+-- V004__seed_data.sql
+-- Insert initial seed data (sample rules and lists)
+-- PostgreSQL 14+
+
+-- ============================================================================
+-- Seed data for rules table
+-- Initial fraud detection rules
+-- ============================================================================
+
+-- Rule 1: High value transaction detection
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('high_value_tx', 1, 'amount > 1000', 'published', 100, 'Flag transactions above 1000 EUR', 'system', NOW());
+
+-- Rule 2: Velocity check - multiple transactions in short time
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('velocity_check', 1, 'velocity(card_id, 5m).count >= 3', 'published', 90, 'Detect 3+ transactions within 5 minutes', 'system', NOW());
+
+-- Rule 3: Geographic mismatch detection
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('geo_mismatch', 1, 'geo != user_home_geo AND amount > 500', 'published', 85, 'Detect transactions from different country than user home', 'system', NOW());
+
+-- Rule 4: Deny list check
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('deny_list_check', 1, 'ip IN deny_list OR device_id IN deny_list', 'published', 95, 'Check if IP or device is in deny list', 'system', NOW());
+
+-- Rule 5: High risk device detection
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('high_risk_device', 1, 'device_risk = ''HIGH'' AND amount > 100', 'published', 80, 'Flag transactions from high-risk devices', 'system', NOW());
+
+-- Rule 6: Unusual merchant category
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('unusual_mcc', 1, 'merchant.mcc IN [''6211'', ''7995''] AND amount > 200', 'published', 75, 'Flag risky merchant categories (securities, gambling)', 'system', NOW());
+
+-- Rule 7: Night time transaction
+INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
+('night_transaction', 1, 'hour(ts) >= 23 OR hour(ts) <= 5', 'published', 70, 'Flag transactions during night hours', 'system', NOW());
+
+-- ============================================================================
+-- Seed data for lists table
+-- Initial allow/deny lists
+-- ============================================================================
+
+-- Deny list: Known fraudulent IPs
+INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
+('deny_ip', 'deny', '192.0.2.1', '{"reason": "Known fraud IP", "added_by": "system"}'::jsonb, NOW()),
+('deny_ip', 'deny', '198.51.100.42', '{"reason": "Suspicious activity", "added_by": "system"}'::jsonb, NOW()),
+('deny_ip', 'deny', '203.0.113.89', '{"reason": "Multiple fraud attempts", "added_by": "system"}'::jsonb, NOW());
+
+-- Deny list: Known fraudulent devices
+INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
+('deny_device', 'deny', 'device_abc123', '{"reason": "Compromised device", "added_by": "security_team"}'::jsonb, NOW()),
+('deny_device', 'deny', 'device_xyz789', '{"reason": "Fraudulent activity detected", "added_by": "security_team"}'::jsonb, NOW());
+
+-- Allow list: Trusted merchants
+INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
+('allow_merchant', 'allow', 'merchant_safe001', '{"reason": "Verified legitimate merchant", "added_by": "system"}'::jsonb, NOW()),
+('allow_merchant', 'allow', 'merchant_safe002', '{"reason": "Long-standing partner", "added_by": "system"}'::jsonb, NOW()),
+('allow_merchant', 'allow', 'merchant_safe003', '{"reason": "Government entity", "added_by": "system"}'::jsonb, NOW());
+
+-- Monitor list: IPs to watch
+INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
+('monitor_ip', 'monitor', '192.0.2.100', '{"reason": "Suspicious pattern observed", "added_by": "analyst"}'::jsonb, NOW()),
+('monitor_ip', 'monitor', '198.51.100.200', '{"reason": "Multiple failed attempts", "added_by": "analyst"}'::jsonb, NOW());
+
+-- High-risk countries list
+INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
+('high_risk_country', 'monitor', 'XX', '{"reason": "High fraud rate country", "added_by": "system"}'::jsonb, NOW()),
+('high_risk_country', 'monitor', 'YY', '{"reason": "Sanctions list", "added_by": "compliance"}'::jsonb, NOW());

---

### 2. Model Serving Service
**Branch**: `feature/model-serving`  
**Description**: PR_MODEL_SERVING.md  
**Fichiers**: 9 fichiers Python + Docker (658 lignes)  
**Status**: ✅ Prêt pour review

M	README.md

---

### 3. Decision Engine Service
**Branch**: `feature/decision-engine`  
**Description**: PR_DECISION_ENGINE.md  
**Fichiers**: 10 fichiers (1574 lignes)  
**Status**: ✅ Prêt pour review

M	README.md

---

### 4. Rules Service
**Branch**: `feature/rules-service`  
**Description**: PR_RULES_SERVICE.md  
**Fichiers**: 9 fichiers (1642 lignes)  
**Status**: ✅ Prêt pour review

M	README.md

---

## 📊 Résumé des changements

| Service | Branch | Fichiers | Lignes | Status |
|---------|--------|----------|--------|--------|
| Database Migrations | feature/database-migrations | 4 | 344 | ✅ Ready |
| Model Serving | feature/model-serving | 9 | 658 | ✅ Ready |
| Decision Engine | feature/decision-engine | 10 | 1574 | ✅ Ready |
| Rules Service | feature/rules-service | 9 | 1642 | ✅ Ready |
| **TOTAL** | **4 branches** | **32** | **4218** | **4/4 Ready** |

---

## 🚀 Process de merge recommandé

### Ordre de merge (dépendances)

1. **Database Migrations** (base de tout)
   M	README.md
Your branch is up to date with 'origin/main'.
Updating cc3b3cc..3dbb40b
Fast-forward
 platform/postgres/migrations/V001__init.sql      | 180 +++++++++++++++++++++++
 platform/postgres/migrations/V002__indices.sql   |  57 +++++++
 platform/postgres/migrations/V003__triggers.sql  |  39 +++++
 platform/postgres/migrations/V004__seed_data.sql |  68 +++++++++
 4 files changed, 344 insertions(+)
 create mode 100644 platform/postgres/migrations/V001__init.sql
 create mode 100644 platform/postgres/migrations/V002__indices.sql
 create mode 100644 platform/postgres/migrations/V003__triggers.sql
 create mode 100644 platform/postgres/migrations/V004__seed_data.sql

2. **Model Serving** (indépendant)
   Updating 3dbb40b..39ea9c2
Fast-forward
 services/model-serving/.dockerignore        |  39 +++
 services/model-serving/Dockerfile           |  58 ++++
 services/model-serving/README.md            |  71 +++++
 services/model-serving/app/__init__.py      |   3 +
 services/model-serving/app/config.py        |  42 +++
 services/model-serving/app/inference.py     | 138 +++++++++
 services/model-serving/app/main.py          | 238 ++++++++++++++++
 services/model-serving/app/models.py        |  61 ++++
 services/model-serving/requirements.txt     |   8 +
 services/rules-service/Dockerfile           |  32 +++
 services/rules-service/README.md            | 379 +++++++++++++++++++++++++
 services/rules-service/app/__init__.py      |   4 +
 services/rules-service/app/config.py        |  52 ++++
 services/rules-service/app/lists_checker.py | 239 ++++++++++++++++
 services/rules-service/app/main.py          | 426 ++++++++++++++++++++++++++++
 services/rules-service/app/models.py        | 153 ++++++++++
 services/rules-service/app/rules_engine.py  | 335 ++++++++++++++++++++++
 services/rules-service/requirements.txt     |  22 ++
 18 files changed, 2300 insertions(+)
 create mode 100644 services/model-serving/.dockerignore
 create mode 100644 services/model-serving/Dockerfile
 create mode 100644 services/model-serving/README.md
 create mode 100644 services/model-serving/app/__init__.py
 create mode 100644 services/model-serving/app/config.py
 create mode 100644 services/model-serving/app/inference.py
 create mode 100644 services/model-serving/app/main.py
 create mode 100644 services/model-serving/app/models.py
 create mode 100644 services/model-serving/requirements.txt
 create mode 100644 services/rules-service/Dockerfile
 create mode 100644 services/rules-service/README.md
 create mode 100644 services/rules-service/app/__init__.py
 create mode 100644 services/rules-service/app/config.py
 create mode 100644 services/rules-service/app/lists_checker.py
 create mode 100644 services/rules-service/app/main.py
 create mode 100644 services/rules-service/app/models.py
 create mode 100644 services/rules-service/app/rules_engine.py
 create mode 100644 services/rules-service/requirements.txt

3. **Rules Service** (indépendant)
   Already up to date.

4. **Decision Engine** (dépend de Model Serving + Rules Service)
   Updating 39ea9c2..c71f78c
Fast-forward
 services/decision-engine/Dockerfile            |  45 ++++
 services/decision-engine/README.md             | 349 +++++++++++++++++++++++++
 services/decision-engine/app/__init__.py       |   0
 services/decision-engine/app/config.py         |  80 ++++++
 services/decision-engine/app/idempotency.py    | 102 ++++++++
 services/decision-engine/app/kafka_producer.py | 144 ++++++++++
 services/decision-engine/app/main.py           | 295 +++++++++++++++++++++
 services/decision-engine/app/models.py         |  84 ++++++
 services/decision-engine/app/orchestrator.py   | 249 ++++++++++++++++++
 services/decision-engine/app/storage.py        | 202 ++++++++++++++
 services/decision-engine/requirements.txt      |  24 ++
 11 files changed, 1574 insertions(+)
 create mode 100644 services/decision-engine/Dockerfile
 create mode 100644 services/decision-engine/README.md
 create mode 100644 services/decision-engine/app/__init__.py
 create mode 100644 services/decision-engine/app/config.py
 create mode 100644 services/decision-engine/app/idempotency.py
 create mode 100644 services/decision-engine/app/kafka_producer.py
 create mode 100644 services/decision-engine/app/main.py
 create mode 100644 services/decision-engine/app/models.py
 create mode 100644 services/decision-engine/app/orchestrator.py
 create mode 100644 services/decision-engine/app/storage.py
 create mode 100644 services/decision-engine/requirements.txt

---

## ✅ Checklist avant merge

Pour chaque PR:

- [ ] Code review effectué
- [ ] Tests unitaires passent (si présents)
- [ ] Docker build réussi
- [ ] Documentation à jour
- [ ] Pas de conflits avec main
- [ ] Variables d environnement documentées
- [ ] Métriques Prometheus configurées

---

## 🔧 Tester toute la stack

Après merge de toutes les branches:

M	README.md
Your branch is ahead of 'origin/main' by 4 commits.
  (use "git push" to publish your local commits)
docker compose up -d

---

## 📝 Notes

- Toutes les branches sont créées à partir de `main`
- Chaque service est indépendant (microservices)
- Docker Compose intègre tous les services
- Prometheus + Grafana pour monitoring

---

## 👥 Reviewers suggérés

- **Database**: @dba-team @backend-team
- **Model Serving**: @ml-team @backend-team
- **Decision Engine**: @backend-team @fraud-team
- **Rules Service**: @backend-team @fraud-team

---

## 📞 Support

Questions? Contactez l équipe backend ou consultez:
- docs/ARCHITECTURE.md
- docs/FLUX-DONNEES.md
- README.md de chaque service
