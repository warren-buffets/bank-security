-- V001__init.sql
-- Create all core tables for fraud detection platform
-- PostgreSQL 14+

-- ============================================================================
-- Table: events
-- Stores all incoming transactional events (source of truth)
-- ============================================================================

CREATE TABLE events (
    event_id        VARCHAR PRIMARY KEY,
    tenant_id       VARCHAR NOT NULL,
    ts              TIMESTAMPTZ NOT NULL,
    type            VARCHAR NOT NULL,
    payload_json    JSONB NOT NULL,
    idem_key        VARCHAR NOT NULL,
    hash            BYTEA NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE events IS 'Stores all incoming transactional events (source of truth)';
COMMENT ON COLUMN events.event_id IS 'Unique transaction ID';
COMMENT ON COLUMN events.tenant_id IS 'Multi-tenant isolation';
COMMENT ON COLUMN events.ts IS 'Transaction timestamp';
COMMENT ON COLUMN events.type IS 'Event type: card_payment, withdrawal, etc.';
COMMENT ON COLUMN events.payload_json IS 'Full event payload in JSON format';
COMMENT ON COLUMN events.idem_key IS 'Idempotency key (24h TTL)';
COMMENT ON COLUMN events.hash IS 'SHA256 hash for integrity verification';

-- ============================================================================
-- Table: decisions
-- Stores fraud decisions (immutable, audit trail)
-- ============================================================================

CREATE TABLE decisions (
    decision_id     VARCHAR PRIMARY KEY,
    event_id        VARCHAR NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    tenant_id       VARCHAR NOT NULL,
    decision        VARCHAR NOT NULL CHECK(decision IN ('ALLOW','CHALLENGE','DENY')),
    score           NUMERIC(5,4),
    rule_hits       TEXT[] NOT NULL DEFAULT '{}',
    reasons         TEXT[] NOT NULL DEFAULT '{}',
    thresholds      JSONB,
    latency_ms      INTEGER NOT NULL,
    model_version   VARCHAR NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE decisions IS 'Stores fraud decisions (immutable, audit trail)';
COMMENT ON COLUMN decisions.decision_id IS 'Unique decision ID';
COMMENT ON COLUMN decisions.event_id IS 'Reference to events table';
COMMENT ON COLUMN decisions.decision IS 'Decision outcome: ALLOW, CHALLENGE, or DENY';
COMMENT ON COLUMN decisions.score IS 'ML fraud score [0..1]';
COMMENT ON COLUMN decisions.rule_hits IS 'Array of rule IDs that were triggered';
COMMENT ON COLUMN decisions.reasons IS 'Human-readable reasons for decision';
COMMENT ON COLUMN decisions.thresholds IS 'Decision thresholds used';
COMMENT ON COLUMN decisions.latency_ms IS 'Processing time in milliseconds';
COMMENT ON COLUMN decisions.model_version IS 'ML model version used';

-- ============================================================================
-- Table: rules
-- Stores detection rules (versioned)
-- ============================================================================

CREATE TABLE rules (
    rule_id         VARCHAR NOT NULL,
    version         INTEGER NOT NULL,
    dsl             TEXT NOT NULL,
    status          VARCHAR NOT NULL CHECK(status IN ('draft','published','disabled')),
    priority        INTEGER DEFAULT 0,
    description     TEXT,
    created_by      VARCHAR NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (rule_id, version)
);

COMMENT ON TABLE rules IS 'Stores detection rules (versioned)';
COMMENT ON COLUMN rules.rule_id IS 'Rule identifier';
COMMENT ON COLUMN rules.version IS 'Rule version number';
COMMENT ON COLUMN rules.dsl IS 'Rule DSL expression';
COMMENT ON COLUMN rules.status IS 'Rule status: draft, published, or disabled';
COMMENT ON COLUMN rules.priority IS 'Execution order priority';
COMMENT ON COLUMN rules.created_by IS 'User who created the rule';

-- ============================================================================
-- Table: lists
-- Stores allow/deny lists (IP, devices, merchants, etc.)
-- ============================================================================

CREATE TABLE lists (
    list_id         VARCHAR NOT NULL,
    type            VARCHAR NOT NULL CHECK(type IN ('allow','deny','monitor')),
    value           VARCHAR NOT NULL,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (list_id, value)
);

COMMENT ON TABLE lists IS 'Stores allow/deny lists for IPs, devices, merchants, etc.';
COMMENT ON COLUMN lists.list_id IS 'List identifier (e.g., deny_ip, allow_merchant)';
COMMENT ON COLUMN lists.type IS 'List type: allow, deny, or monitor';
COMMENT ON COLUMN lists.value IS 'List value (IP, device_id, merchant_id, etc.)';
COMMENT ON COLUMN lists.metadata IS 'Additional metadata (reason, expires_at, etc.)';

-- ============================================================================
-- Table: cases
-- Stores fraud cases for manual investigation
-- ============================================================================

CREATE TABLE cases (
    case_id         VARCHAR PRIMARY KEY,
    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
    queue           VARCHAR NOT NULL,
    status          VARCHAR NOT NULL CHECK(status IN ('open','in_progress','closed')),
    assignee        VARCHAR,
    priority        INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    resolution      VARCHAR
);

COMMENT ON TABLE cases IS 'Stores fraud cases for manual investigation';
COMMENT ON COLUMN cases.case_id IS 'Unique case identifier';
COMMENT ON COLUMN cases.event_id IS 'Reference to events table';
COMMENT ON COLUMN cases.queue IS 'Case queue (high_risk, medium_risk, review)';
COMMENT ON COLUMN cases.status IS 'Case status: open, in_progress, or closed';
COMMENT ON COLUMN cases.assignee IS 'Analyst user ID';
COMMENT ON COLUMN cases.priority IS 'Priority: 0=low, 1=medium, 2=high';
COMMENT ON COLUMN cases.resolution IS 'Final resolution (fraud_confirmed, false_positive, etc.)';

-- ============================================================================
-- Table: labels
-- Stores ground truth labels (feedback loop for ML)
-- ============================================================================

CREATE TABLE labels (
    event_id        VARCHAR NOT NULL REFERENCES events(event_id),
    label           VARCHAR NOT NULL CHECK(label IN ('fraud','legit','chargeback','fp')),
    source          VARCHAR NOT NULL,
    confidence      NUMERIC(3,2),
    ts              TIMESTAMPTZ NOT NULL,
    metadata        JSONB,
    PRIMARY KEY (event_id, label, source)
);

COMMENT ON TABLE labels IS 'Stores ground truth labels for ML training';
COMMENT ON COLUMN labels.event_id IS 'Reference to events table';
COMMENT ON COLUMN labels.label IS 'Label type: fraud, legit, chargeback, or fp (false positive)';
COMMENT ON COLUMN labels.source IS 'Label source (analyst, customer, chargeback_system)';
COMMENT ON COLUMN labels.confidence IS 'Confidence score [0.0 to 1.0]';

-- ============================================================================
-- Table: audit_logs
-- Stores all critical changes (immutable, signed)
-- ============================================================================

CREATE TABLE audit_logs (
    log_id          BIGSERIAL PRIMARY KEY,
    actor           VARCHAR NOT NULL,
    action          VARCHAR NOT NULL,
    entity          VARCHAR NOT NULL,
    entity_id       VARCHAR NOT NULL,
    before          JSONB,
    after           JSONB,
    ts              TIMESTAMPTZ DEFAULT NOW(),
    signature       BYTEA NOT NULL,
    prev_log_hash   BYTEA
);

COMMENT ON TABLE audit_logs IS 'Stores all critical changes (immutable, signed)';
COMMENT ON COLUMN audit_logs.actor IS 'User or service who made the change';
COMMENT ON COLUMN audit_logs.action IS 'Action type: CREATE, UPDATE, DELETE';
COMMENT ON COLUMN audit_logs.entity IS 'Table name';
COMMENT ON COLUMN audit_logs.entity_id IS 'Primary key of the entity';
COMMENT ON COLUMN audit_logs.before IS 'State before change';
COMMENT ON COLUMN audit_logs.after IS 'State after change';
COMMENT ON COLUMN audit_logs.signature IS 'HMAC-SHA256 signature';
COMMENT ON COLUMN audit_logs.prev_log_hash IS 'Hash of previous log (chain)';
