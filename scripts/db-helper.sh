#!/bin/bash
# FraudGuard AI - Database Helper Script
# Usage: ./scripts/db-helper.sh [command]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Database connection
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-antifraud}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-postgres_dev}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Execute SQL
psql_exec() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

# Connect to database
connect() {
    log_info "Connecting to $DB_NAME on $DB_HOST:$DB_PORT..."
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
}

# Run migrations
migrate() {
    log_info "Running database migrations..."
    for f in platform/postgres/migrations/*.sql; do
        log_info "Applying $(basename "$f")..."
        psql_exec -f "$f" 2>/dev/null || log_warn "Migration may have already been applied"
    done
    log_success "Migrations complete."
}

# Show table sizes
sizes() {
    log_info "Table sizes:"
    psql_exec -c "
        SELECT
            schemaname || '.' || tablename AS table_name,
            pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
            pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS data_size,
            pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS index_size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
    "
}

# Show recent events
recent_events() {
    local limit=${1:-10}
    log_info "Last $limit events:"
    psql_exec -c "
        SELECT
            event_id,
            event_type,
            amount,
            currency,
            created_at
        FROM events
        ORDER BY created_at DESC
        LIMIT $limit;
    "
}

# Show recent decisions
recent_decisions() {
    local limit=${1:-10}
    log_info "Last $limit decisions:"
    psql_exec -c "
        SELECT
            decision_id,
            event_id,
            decision,
            score,
            created_at
        FROM decisions
        ORDER BY created_at DESC
        LIMIT $limit;
    "
}

# Decision statistics
decision_stats() {
    log_info "Decision statistics:"
    psql_exec -c "
        SELECT
            decision,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage,
            ROUND(AVG(score)::numeric, 4) as avg_score,
            ROUND(MIN(score)::numeric, 4) as min_score,
            ROUND(MAX(score)::numeric, 4) as max_score
        FROM decisions
        GROUP BY decision
        ORDER BY count DESC;
    "
}

# Active rules
active_rules() {
    log_info "Active rules:"
    psql_exec -c "
        SELECT
            rule_id,
            rule_name,
            severity,
            action,
            is_active,
            updated_at
        FROM rules
        WHERE is_active = true
        ORDER BY severity DESC, rule_name;
    "
}

# Deny list entries
deny_list() {
    log_info "Deny list entries:"
    psql_exec -c "
        SELECT
            list_id,
            list_type,
            value,
            reason,
            expires_at,
            created_at
        FROM lists
        WHERE list_type = 'deny'
        AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY created_at DESC
        LIMIT 20;
    "
}

# Allow list entries
allow_list() {
    log_info "Allow list entries:"
    psql_exec -c "
        SELECT
            list_id,
            list_type,
            value,
            reason,
            expires_at,
            created_at
        FROM lists
        WHERE list_type = 'allow'
        AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY created_at DESC
        LIMIT 20;
    "
}

# Fraud rate by hour
fraud_by_hour() {
    log_info "Fraud rate by hour of day:"
    psql_exec -c "
        SELECT
            EXTRACT(HOUR FROM e.created_at) as hour,
            COUNT(*) as total,
            SUM(CASE WHEN d.decision = 'DENY' THEN 1 ELSE 0 END) as denied,
            ROUND(SUM(CASE WHEN d.decision = 'DENY' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as deny_rate
        FROM events e
        JOIN decisions d ON e.event_id = d.event_id
        GROUP BY EXTRACT(HOUR FROM e.created_at)
        ORDER BY hour;
    "
}

# High risk transactions
high_risk() {
    local threshold=${1:-0.7}
    log_info "High risk transactions (score > $threshold):"
    psql_exec -c "
        SELECT
            d.decision_id,
            e.event_id,
            e.amount,
            e.currency,
            d.score,
            d.decision,
            d.created_at
        FROM decisions d
        JOIN events e ON d.event_id = e.event_id
        WHERE d.score > $threshold
        ORDER BY d.score DESC
        LIMIT 20;
    "
}

# Create backup
backup() {
    local backup_file="backup_${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
    log_info "Creating backup: $backup_file"
    PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$backup_file"
    log_success "Backup created: $backup_file"
}

# Reset database (dangerous!)
reset_db() {
    log_warn "This will DELETE ALL DATA in the database!"
    read -p "Type 'RESET' to confirm: " confirm
    if [ "$confirm" = "RESET" ]; then
        log_info "Resetting database..."
        psql_exec -c "
            TRUNCATE events, decisions, cases, labels, audit_logs CASCADE;
        "
        log_success "Database reset complete."
    else
        log_info "Reset cancelled."
    fi
}

# Show help
help() {
    echo "FraudGuard AI - Database Helper"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Connection:"
    echo "  connect           Open psql shell"
    echo "  migrate           Run all migrations"
    echo ""
    echo "Queries:"
    echo "  sizes             Show table sizes"
    echo "  recent_events [n] Show recent events (default: 10)"
    echo "  recent_decisions  Show recent decisions"
    echo "  decision_stats    Decision statistics"
    echo "  active_rules      List active rules"
    echo "  deny_list         Show deny list entries"
    echo "  allow_list        Show allow list entries"
    echo "  fraud_by_hour     Fraud rate by hour"
    echo "  high_risk [score] High risk transactions (default: 0.7)"
    echo ""
    echo "Maintenance:"
    echo "  backup            Create SQL backup"
    echo "  reset_db          Reset all data (DANGEROUS)"
    echo "  help              Show this help"
    echo ""
    echo "Environment:"
    echo "  POSTGRES_HOST=$DB_HOST"
    echo "  POSTGRES_PORT=$DB_PORT"
    echo "  POSTGRES_DB=$DB_NAME"
    echo "  POSTGRES_USER=$DB_USER"
}

# Main
case "${1:-help}" in
    connect) connect ;;
    migrate) migrate ;;
    sizes) sizes ;;
    recent_events) recent_events "$2" ;;
    recent_decisions) recent_decisions "$2" ;;
    decision_stats) decision_stats ;;
    active_rules) active_rules ;;
    deny_list) deny_list ;;
    allow_list) allow_list ;;
    fraud_by_hour) fraud_by_hour ;;
    high_risk) high_risk "$2" ;;
    backup) backup ;;
    reset_db) reset_db ;;
    help|*) help ;;
esac
