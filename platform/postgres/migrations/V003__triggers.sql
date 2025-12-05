-- V003__triggers.sql
-- Create immutability triggers for decisions and audit_logs tables
-- PostgreSQL 14+

-- ============================================================================
-- Immutability trigger for decisions table
-- Prevents any updates to decisions once created (audit trail requirement)
-- ============================================================================

CREATE OR REPLACE FUNCTION prevent_decision_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Decisions are immutable. Create a new decision instead.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_immutable_decisions
BEFORE UPDATE ON decisions
FOR EACH ROW EXECUTE FUNCTION prevent_decision_update();

-- ============================================================================
-- Immutability triggers for audit_logs table
-- Prevents any updates or deletes (WORM - Write Once Read Many)
-- ============================================================================

CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable. No modifications allowed.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_immutable_audit_logs_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();

CREATE TRIGGER trigger_immutable_audit_logs_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
