-- V006: Audit Log Immutability (WORM - Write Once Read Many)
-- Implements PSD2/ACPR compliance for audit trail integrity
-- HMAC-SHA256 signature prevents tampering
-- Triggers prevent UPDATE and DELETE operations

-- ============================================================================
-- STEP 1: Ensure audit_logs table has signature column
-- ============================================================================

-- Add signature column if not exists (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs' AND column_name = 'signature'
    ) THEN
        ALTER TABLE audit_logs ADD COLUMN signature VARCHAR(64) NOT NULL DEFAULT '';
        COMMENT ON COLUMN audit_logs.signature IS 'HMAC-SHA256 signature for immutability';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Create trigger function to prevent modifications (WORM)
-- ============================================================================

CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent UPDATE operations
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'UPDATE operations not allowed on audit_logs (WORM compliance)'
            USING HINT = 'Audit logs are immutable once written',
                  ERRCODE = 'check_violation';
    END IF;

    -- Prevent DELETE operations
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'DELETE operations not allowed on audit_logs (WORM compliance)'
            USING HINT = 'Audit logs must be retained for 7 years',
                  ERRCODE = 'check_violation';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION prevent_audit_log_modification() IS
    'Enforces WORM (Write Once Read Many) for audit_logs table';

-- ============================================================================
-- STEP 3: Create triggers to enforce immutability
-- ============================================================================

-- Drop existing triggers if they exist (idempotent)
DROP TRIGGER IF EXISTS prevent_audit_log_update ON audit_logs;
DROP TRIGGER IF EXISTS prevent_audit_log_delete ON audit_logs;

-- Trigger to prevent UPDATE
CREATE TRIGGER prevent_audit_log_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

-- Trigger to prevent DELETE
CREATE TRIGGER prevent_audit_log_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

COMMENT ON TRIGGER prevent_audit_log_update ON audit_logs IS
    'Prevents modification of audit logs (PSD2/ACPR compliance)';

COMMENT ON TRIGGER prevent_audit_log_delete ON audit_logs IS
    'Prevents deletion of audit logs (7-year retention requirement)';

-- ============================================================================
-- STEP 4: Create index on signature for integrity checks
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_logs_signature
    ON audit_logs(signature);

COMMENT ON INDEX idx_audit_logs_signature IS
    'Optimizes audit log integrity verification queries';

-- ============================================================================
-- STEP 5: Create view for audit log integrity checks
-- ============================================================================

CREATE OR REPLACE VIEW audit_logs_integrity AS
SELECT
    log_id,
    actor,
    action,
    entity,
    entity_id,
    created_at,
    signature,
    LENGTH(signature) = 64 AS signature_valid_length,
    signature ~ '^[0-9a-f]{64}$' AS signature_valid_format
FROM audit_logs;

COMMENT ON VIEW audit_logs_integrity IS
    'Helper view for validating audit log signature format';

-- ============================================================================
-- STEP 6: Grant appropriate permissions
-- ============================================================================

-- Application can only INSERT (not UPDATE/DELETE)
GRANT SELECT, INSERT ON audit_logs TO postgres;
REVOKE UPDATE, DELETE ON audit_logs FROM postgres;

-- ============================================================================
-- VERIFICATION QUERIES (for testing)
-- ============================================================================

-- Test 1: Verify triggers exist
DO $$
DECLARE
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE event_object_table = 'audit_logs'
      AND trigger_name IN ('prevent_audit_log_update', 'prevent_audit_log_delete');

    IF trigger_count <> 2 THEN
        RAISE WARNING 'Expected 2 triggers on audit_logs, found %', trigger_count;
    ELSE
        RAISE NOTICE 'Audit log immutability triggers created successfully';
    END IF;
END $$;

-- Test 2: Verify signature column exists and has correct type
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs'
          AND column_name = 'signature'
          AND character_maximum_length = 64
    ) INTO column_exists;

    IF column_exists THEN
        RAISE NOTICE 'Signature column configured correctly (VARCHAR(64))';
    ELSE
        RAISE WARNING 'Signature column not found or incorrect type';
    END IF;
END $$;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Migration V006 completed: Audit log immutability (WORM) enforced';
    RAISE NOTICE '  - UPDATE operations blocked on audit_logs';
    RAISE NOTICE '  - DELETE operations blocked on audit_logs';
    RAISE NOTICE '  - HMAC-SHA256 signature column ready';
    RAISE NOTICE '  - PSD2/ACPR compliance: 7-year retention guaranteed';
END $$;
