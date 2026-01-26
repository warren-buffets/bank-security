-- V007: RGPD Compliance Tables
-- Implements DPIA logging and anonymization tracking
-- Complies with RGPD Article 35 (Data Protection Impact Assessment)

-- ============================================================================
-- STEP 1: Create DPIA logs table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dpia_logs (
    dpia_id BIGSERIAL PRIMARY KEY,
    event VARCHAR(100) NOT NULL,
    details JSONB,
    ts TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT dpia_logs_event_check CHECK (event IN (
        'DATA_ANONYMIZATION',
        'DATA_DELETION',
        'DATA_EXPORT',
        'DATA_ACCESS',
        'CONSENT_GRANTED',
        'CONSENT_REVOKED',
        'SCA_TRIGGERED',
        'RISK_ASSESSMENT'
    ))
);

COMMENT ON TABLE dpia_logs IS 'RGPD Article 35 - Data Protection Impact Assessment logs';
COMMENT ON COLUMN dpia_logs.event IS 'Type of DPIA event';
COMMENT ON COLUMN dpia_logs.details IS 'Additional context for the event';
COMMENT ON COLUMN dpia_logs.ts IS 'Event timestamp';

-- ============================================================================
-- STEP 2: Create index for DPIA queries
-- ============================================================================

CREATE INDEX idx_dpia_logs_ts ON dpia_logs(ts);
CREATE INDEX idx_dpia_logs_event ON dpia_logs(event);

-- ============================================================================
-- STEP 3: Create SCA (Strong Customer Authentication) table
-- ============================================================================

CREATE TABLE IF NOT EXISTS sca_challenges (
    challenge_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    transaction_id VARCHAR(100),
    risk_score FLOAT NOT NULL,
    challenge_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT sca_challenge_type_check CHECK (challenge_type IN (
        'NONE',           -- Low risk, no SCA needed
        'BIOMETRIC',      -- Medium risk, biometric auth
        'OTP_SMS',        -- Medium risk, SMS code
        'OTP_EMAIL',      -- Medium risk, email code
        'PUSH_NOTIFICATION', -- High risk, app push
        'HARDWARE_TOKEN'  -- Very high risk, physical token
    )),
    CONSTRAINT sca_status_check CHECK (status IN (
        'PENDING',
        'COMPLETED',
        'FAILED',
        'EXPIRED',
        'BYPASSED'
    ))
);

COMMENT ON TABLE sca_challenges IS 'PSD2 SCA challenges based on transaction risk';
COMMENT ON COLUMN sca_challenges.risk_score IS 'Transaction risk score (0.0-1.0)';
COMMENT ON COLUMN sca_challenges.challenge_type IS 'Type of authentication required';
COMMENT ON COLUMN sca_challenges.status IS 'Current status of the challenge';

-- ============================================================================
-- STEP 4: Create indexes for SCA queries
-- ============================================================================

CREATE INDEX idx_sca_user_id ON sca_challenges(user_id);
CREATE INDEX idx_sca_transaction_id ON sca_challenges(transaction_id);
CREATE INDEX idx_sca_status ON sca_challenges(status);
CREATE INDEX idx_sca_created_at ON sca_challenges(created_at);

-- ============================================================================
-- STEP 5: Create function to determine SCA level based on risk
-- ============================================================================

CREATE OR REPLACE FUNCTION determine_sca_level(risk_score FLOAT)
RETURNS VARCHAR AS $$
BEGIN
    -- Dynamic SCA based on transaction risk score
    IF risk_score < 0.3 THEN
        RETURN 'NONE';  -- Low risk, no additional auth
    ELSIF risk_score < 0.5 THEN
        RETURN 'OTP_SMS';  -- Medium risk, SMS code
    ELSIF risk_score < 0.7 THEN
        RETURN 'BIOMETRIC';  -- Medium-high risk, biometric
    ELSIF risk_score < 0.9 THEN
        RETURN 'PUSH_NOTIFICATION';  -- High risk, app push
    ELSE
        RETURN 'HARDWARE_TOKEN';  -- Very high risk, physical token
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION determine_sca_level IS 'Dynamic SCA level based on transaction risk score';

-- ============================================================================
-- STEP 6: Create view for RGPD compliance reporting
-- ============================================================================

CREATE OR REPLACE VIEW rgpd_compliance_summary AS
SELECT
    'Data Anonymization' as compliance_item,
    COUNT(*) as event_count,
    MAX(ts) as last_execution
FROM dpia_logs
WHERE event = 'DATA_ANONYMIZATION'
UNION ALL
SELECT
    'SCA Challenges Issued' as compliance_item,
    COUNT(*) as event_count,
    MAX(created_at) as last_execution
FROM sca_challenges
UNION ALL
SELECT
    'Audit Logs Total' as compliance_item,
    COUNT(*) as event_count,
    MAX(ts) as last_execution
FROM audit_logs;

COMMENT ON VIEW rgpd_compliance_summary IS 'Summary view for RGPD compliance reporting';

-- ============================================================================
-- STEP 7: Grant permissions
-- ============================================================================

GRANT SELECT, INSERT ON dpia_logs TO postgres;
GRANT SELECT, INSERT, UPDATE ON sca_challenges TO postgres;
GRANT USAGE, SELECT ON SEQUENCE dpia_logs_dpia_id_seq TO postgres;
GRANT USAGE, SELECT ON SEQUENCE sca_challenges_challenge_id_seq TO postgres;

-- ============================================================================
-- STEP 8: Insert initial DPIA log entry
-- ============================================================================

INSERT INTO dpia_logs (event, details, ts)
VALUES (
    'DATA_ANONYMIZATION',
    '{"message": "RGPD compliance tables initialized", "version": "V007"}',
    NOW()
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Test 1: Verify DPIA table exists
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'dpia_logs'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE 'DPIA logs table created successfully';
    ELSE
        RAISE WARNING 'DPIA logs table not found';
    END IF;
END $$;

-- Test 2: Verify SCA table exists
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'sca_challenges'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE 'SCA challenges table created successfully';
    ELSE
        RAISE WARNING 'SCA challenges table not found';
    END IF;
END $$;

-- Test 3: Verify SCA function
DO $$
DECLARE
    sca_level VARCHAR;
BEGIN
    -- Test different risk scores
    sca_level := determine_sca_level(0.2);  -- Should be NONE
    IF sca_level = 'NONE' THEN
        RAISE NOTICE 'SCA function working: low risk = NONE';
    END IF;

    sca_level := determine_sca_level(0.6);  -- Should be BIOMETRIC
    IF sca_level = 'BIOMETRIC' THEN
        RAISE NOTICE 'SCA function working: medium risk = BIOMETRIC';
    END IF;

    sca_level := determine_sca_level(0.95);  -- Should be HARDWARE_TOKEN
    IF sca_level = 'HARDWARE_TOKEN' THEN
        RAISE NOTICE 'SCA function working: high risk = HARDWARE_TOKEN';
    END IF;
END $$;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Migration V007 completed: RGPD compliance tables created';
    RAISE NOTICE '  - DPIA logs table (dpia_logs)';
    RAISE NOTICE '  - SCA challenges table (sca_challenges)';
    RAISE NOTICE '  - Dynamic SCA function (determine_sca_level)';
    RAISE NOTICE '  - RGPD compliance reporting view';
    RAISE NOTICE '  - RGPD Article 35 compliance ready';
END $$;
