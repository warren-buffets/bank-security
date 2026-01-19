-- V004__seed_data.sql
-- Insert initial seed data (sample rules and lists)
-- PostgreSQL 14+

-- ============================================================================
-- Seed data for rules table
-- Initial fraud detection rules
-- ============================================================================

-- Rule 1: High value transaction detection
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('high_value_tx', 1, 'amount > 1000', 'published', 100, 'Flag transactions above 1000 EUR', 'system', NOW());

-- Rule 2: Velocity check - multiple transactions in short time
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('velocity_check', 1, 'velocity(card_id, 5m).count >= 3', 'published', 90, 'Detect 3+ transactions within 5 minutes', 'system', NOW());

-- Rule 3: Geographic mismatch detection
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('geo_mismatch', 1, 'geo != user_home_geo AND amount > 500', 'published', 85, 'Detect transactions from different country than user home', 'system', NOW());

-- Rule 4: Deny list check
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('deny_list_check', 1, 'ip IN deny_list OR device_id IN deny_list', 'published', 95, 'Check if IP or device is in deny list', 'system', NOW());

-- Rule 5: High risk device detection
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('high_risk_device', 1, 'device_risk = ''HIGH'' AND amount > 100', 'published', 80, 'Flag transactions from high-risk devices', 'system', NOW());

-- Rule 6: Unusual merchant category
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('unusual_mcc', 1, 'merchant.mcc IN [''6211'', ''7995''] AND amount > 200', 'published', 75, 'Flag risky merchant categories (securities, gambling)', 'system', NOW());

-- Rule 7: Night time transaction
INSERT INTO rules (rule_id, version, dsl, status, priority, description, created_by, created_at) VALUES
('night_transaction', 1, 'hour(ts) >= 23 OR hour(ts) <= 5', 'published', 70, 'Flag transactions during night hours', 'system', NOW());

-- ============================================================================
-- Seed data for lists table
-- Initial allow/deny lists
-- ============================================================================

-- Deny list: Known fraudulent IPs
INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
('deny_ip', 'deny', '192.0.2.1', '{"reason": "Known fraud IP", "added_by": "system"}'::jsonb, NOW()),
('deny_ip', 'deny', '198.51.100.42', '{"reason": "Suspicious activity", "added_by": "system"}'::jsonb, NOW()),
('deny_ip', 'deny', '203.0.113.89', '{"reason": "Multiple fraud attempts", "added_by": "system"}'::jsonb, NOW());

-- Deny list: Known fraudulent devices
INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
('deny_device', 'deny', 'device_abc123', '{"reason": "Compromised device", "added_by": "security_team"}'::jsonb, NOW()),
('deny_device', 'deny', 'device_xyz789', '{"reason": "Fraudulent activity detected", "added_by": "security_team"}'::jsonb, NOW());

-- Allow list: Trusted merchants
INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
('allow_merchant', 'allow', 'merchant_safe001', '{"reason": "Verified legitimate merchant", "added_by": "system"}'::jsonb, NOW()),
('allow_merchant', 'allow', 'merchant_safe002', '{"reason": "Long-standing partner", "added_by": "system"}'::jsonb, NOW()),
('allow_merchant', 'allow', 'merchant_safe003', '{"reason": "Government entity", "added_by": "system"}'::jsonb, NOW());

-- Monitor list: IPs to watch
INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
('monitor_ip', 'monitor', '192.0.2.100', '{"reason": "Suspicious pattern observed", "added_by": "analyst"}'::jsonb, NOW()),
('monitor_ip', 'monitor', '198.51.100.200', '{"reason": "Multiple failed attempts", "added_by": "analyst"}'::jsonb, NOW());

-- High-risk countries list
INSERT INTO lists (list_id, type, value, metadata, created_at) VALUES
('high_risk_country', 'monitor', 'XX', '{"reason": "High fraud rate country", "added_by": "system"}'::jsonb, NOW()),
('high_risk_country', 'monitor', 'YY', '{"reason": "Sanctions list", "added_by": "compliance"}'::jsonb, NOW());
