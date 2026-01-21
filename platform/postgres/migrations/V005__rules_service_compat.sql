-- V005__rules_service_compat.sql
-- Add compatibility view and columns for rules-service
-- This migration adds the columns expected by the rules-service API

-- ============================================================================
-- Option 1: Add a view that maps existing rules table to expected format
-- ============================================================================

-- Create a view that maps the existing rules table structure to what rules-service expects
CREATE OR REPLACE VIEW rules_active AS
SELECT
    rule_id AS id,
    rule_id AS name,
    dsl AS expression,
    CASE
        WHEN status = 'published' THEN 'deny'
        ELSE 'review'
    END AS action,
    priority,
    status = 'published' AS enabled,
    description,
    '{}'::jsonb AS metadata,
    created_at,
    created_at AS updated_at
FROM rules
WHERE status = 'published';

COMMENT ON VIEW rules_active IS 'View mapping rules table to rules-service expected format';

-- ============================================================================
-- Option 2: Create a dedicated rules_v2 table for rules-service
-- This is the preferred approach for production
-- ============================================================================

CREATE TABLE IF NOT EXISTS rules_v2 (
    id              VARCHAR PRIMARY KEY,
    name            VARCHAR NOT NULL,
    expression      TEXT NOT NULL,
    action          VARCHAR NOT NULL CHECK(action IN ('allow', 'deny', 'review', 'challenge')),
    priority        INTEGER DEFAULT 0,
    enabled         BOOLEAN DEFAULT true,
    description     TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rules_v2 IS 'Rules table compatible with rules-service API';
COMMENT ON COLUMN rules_v2.id IS 'Unique rule identifier';
COMMENT ON COLUMN rules_v2.name IS 'Human-readable rule name';
COMMENT ON COLUMN rules_v2.expression IS 'Rule expression in DSL format';
COMMENT ON COLUMN rules_v2.action IS 'Action when rule matches: allow, deny, review, challenge';
COMMENT ON COLUMN rules_v2.priority IS 'Execution order (higher = first)';
COMMENT ON COLUMN rules_v2.enabled IS 'Whether rule is active';
COMMENT ON COLUMN rules_v2.metadata IS 'Additional rule metadata';

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_rules_v2_enabled_priority ON rules_v2(enabled, priority DESC);

-- ============================================================================
-- Seed default fraud detection rules
-- ============================================================================

INSERT INTO rules_v2 (id, name, expression, action, priority, enabled, description, metadata) VALUES
    -- High-risk rules (priority 100+)
    ('rule_high_amount', 'High Amount Transaction', 'amount > 5000', 'review', 100, true,
     'Flag transactions over 5000 EUR for review', '{"category": "amount", "risk_level": "high"}'),

    ('rule_very_high_amount', 'Very High Amount Transaction', 'amount > 10000', 'deny', 110, true,
     'Block transactions over 10000 EUR', '{"category": "amount", "risk_level": "critical"}'),

    ('rule_night_transaction', 'Night Transaction', 'hour >= 0 AND hour <= 5', 'review', 90, true,
     'Flag transactions between midnight and 5 AM', '{"category": "time", "risk_level": "medium"}'),

    -- Velocity rules (priority 80-99)
    ('rule_high_velocity', 'High Velocity', 'velocity_1h > 5', 'review', 85, true,
     'Flag when more than 5 transactions in 1 hour', '{"category": "velocity", "risk_level": "medium"}'),

    ('rule_extreme_velocity', 'Extreme Velocity', 'velocity_1h > 10', 'deny', 95, true,
     'Block when more than 10 transactions in 1 hour', '{"category": "velocity", "risk_level": "high"}'),

    -- Geographic rules (priority 70-79)
    ('rule_cross_border', 'Cross Border Transaction', 'card_country != merchant_country', 'review', 75, true,
     'Flag cross-border transactions', '{"category": "geographic", "risk_level": "low"}'),

    ('rule_high_risk_country', 'High Risk Country', 'merchant_country IN (''NG'', ''RU'', ''CN'', ''BR'')', 'review', 78, true,
     'Flag transactions in high-risk countries', '{"category": "geographic", "risk_level": "medium"}'),

    -- Category rules (priority 60-69)
    ('rule_gambling', 'Gambling Transaction', 'mcc IN (''7995'', ''7801'', ''7802'')', 'review', 65, true,
     'Flag gambling-related transactions', '{"category": "merchant", "risk_level": "medium"}'),

    ('rule_crypto', 'Cryptocurrency Purchase', 'mcc = ''6051'' AND amount > 1000', 'review', 68, true,
     'Flag large cryptocurrency purchases', '{"category": "merchant", "risk_level": "medium"}'),

    -- Device/Channel rules (priority 50-59)
    ('rule_new_device', 'New Device', 'device_age_days < 1', 'review', 55, true,
     'Flag transactions from newly registered devices', '{"category": "device", "risk_level": "low"}'),

    ('rule_vpn_detected', 'VPN/Proxy Detected', 'proxy_vpn_flag = true AND amount > 500', 'review', 58, true,
     'Flag VPN/proxy transactions over 500 EUR', '{"category": "device", "risk_level": "medium"}')

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    expression = EXCLUDED.expression,
    action = EXCLUDED.action,
    priority = EXCLUDED.priority,
    enabled = EXCLUDED.enabled,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- ============================================================================
-- Create trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_rules_v2_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_rules_v2_updated_at ON rules_v2;
CREATE TRIGGER trigger_rules_v2_updated_at
    BEFORE UPDATE ON rules_v2
    FOR EACH ROW
    EXECUTE FUNCTION update_rules_v2_updated_at();
