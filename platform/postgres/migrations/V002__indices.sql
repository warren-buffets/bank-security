-- V002__indices.sql
-- Create all performance indexes on tables
-- PostgreSQL 14+

-- ============================================================================
-- Indexes for events table
-- ============================================================================

CREATE INDEX idx_events_tenant_ts ON events(tenant_id, ts DESC);
CREATE INDEX idx_events_idem_key ON events(idem_key);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- ============================================================================
-- Indexes for decisions table
-- ============================================================================

CREATE INDEX idx_decisions_event_id ON decisions(event_id);
CREATE INDEX idx_decisions_tenant_decision ON decisions(tenant_id, decision);
CREATE INDEX idx_decisions_created_at ON decisions(created_at DESC);
CREATE INDEX idx_decisions_score ON decisions(score DESC) WHERE score IS NOT NULL;

-- ============================================================================
-- Indexes for rules table
-- ============================================================================

CREATE INDEX idx_rules_status ON rules(status) WHERE status = 'published';

-- ============================================================================
-- Indexes for lists table
-- ============================================================================

CREATE INDEX idx_lists_type_value ON lists(type, value);
CREATE INDEX idx_lists_metadata ON lists USING GIN(metadata);

-- ============================================================================
-- Indexes for cases table
-- ============================================================================

CREATE INDEX idx_cases_queue_status ON cases(queue, status);
CREATE INDEX idx_cases_assignee ON cases(assignee) WHERE status != 'closed';
CREATE INDEX idx_cases_priority ON cases(priority DESC);

-- ============================================================================
-- Indexes for labels table
-- ============================================================================

CREATE INDEX idx_labels_event_id ON labels(event_id);
CREATE INDEX idx_labels_label ON labels(label);

-- ============================================================================
-- Indexes for audit_logs table
-- ============================================================================

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity, entity_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_ts ON audit_logs(ts DESC);
