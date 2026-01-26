#!/bin/bash
# SafeGuard AI - Redis Helper Script
# Usage: ./scripts/redis-helper.sh [command]

set -e

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_CONTAINER="${REDIS_CONTAINER:-safeguard-redis}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Redis CLI command
redis_cmd() {
    docker exec "$REDIS_CONTAINER" redis-cli "$@"
}

# Connect to Redis CLI
connect() {
    log_info "Connecting to Redis..."
    docker exec -it "$REDIS_CONTAINER" redis-cli
}

# Ping Redis
ping() {
    log_info "Pinging Redis..."
    redis_cmd PING
}

# Get server info
info() {
    log_info "Redis server info:"
    redis_cmd INFO server
    echo ""
    log_info "Memory info:"
    redis_cmd INFO memory
}

# Get key count by pattern
count_keys() {
    local pattern=${1:-*}
    log_info "Counting keys matching: $pattern"
    redis_cmd EVAL "return #redis.call('keys', ARGV[1])" 0 "$pattern"
}

# List keys by pattern
list_keys() {
    local pattern=${1:-*}
    local limit=${2:-20}
    log_info "Keys matching: $pattern (limit: $limit)"
    redis_cmd EVAL "local keys = redis.call('keys', ARGV[1]); local result = {}; for i=1,math.min(#keys, tonumber(ARGV[2])) do result[i] = keys[i] end; return result" 0 "$pattern" "$limit"
}

# Get key value
get_key() {
    local key=$1
    log_info "Getting key: $key"
    local type=$(redis_cmd TYPE "$key")
    echo "Type: $type"
    case "$type" in
        string)
            redis_cmd GET "$key"
            ;;
        hash)
            redis_cmd HGETALL "$key"
            ;;
        list)
            redis_cmd LRANGE "$key" 0 -1
            ;;
        set)
            redis_cmd SMEMBERS "$key"
            ;;
        zset)
            redis_cmd ZRANGE "$key" 0 -1 WITHSCORES
            ;;
        *)
            echo "Unknown type: $type"
            ;;
    esac
}

# Delete key
delete_key() {
    local key=$1
    log_info "Deleting key: $key"
    redis_cmd DEL "$key"
    log_success "Key deleted."
}

# Delete keys by pattern (careful!)
delete_pattern() {
    local pattern=$1
    log_info "Deleting keys matching: $pattern"
    redis_cmd EVAL "local keys = redis.call('keys', ARGV[1]); for i=1,#keys do redis.call('del', keys[i]) end; return #keys" 0 "$pattern"
    log_success "Keys deleted."
}

# List idempotency keys
idempotency_keys() {
    log_info "Idempotency keys:"
    list_keys "idem_*" 20
}

# List rule cache
rule_cache() {
    log_info "Rule cache keys:"
    list_keys "rule_*" 20
}

# List feature cache
feature_cache() {
    log_info "Feature cache keys:"
    list_keys "feature_*" 20
}

# Memory analysis
memory() {
    log_info "Memory usage by key pattern:"
    echo "=== Idempotency keys ==="
    redis_cmd MEMORY USAGE "idem_*" 2>/dev/null || echo "N/A"
    echo ""
    log_info "Top keys by memory:"
    redis_cmd EVAL "
        local keys = redis.call('keys', '*')
        local result = {}
        for i=1,math.min(#keys, 10) do
            local mem = redis.call('memory', 'usage', keys[i]) or 0
            result[i] = keys[i] .. ': ' .. mem .. ' bytes'
        end
        return result
    " 0
}

# Clear all idempotency keys
clear_idempotency() {
    log_info "Clearing all idempotency keys..."
    delete_pattern "idem_*"
}

# Clear all caches
clear_cache() {
    log_info "Clearing all cache keys..."
    delete_pattern "cache_*"
    delete_pattern "rule_*"
    delete_pattern "feature_*"
    log_success "Caches cleared."
}

# Flush all (dangerous!)
flush_all() {
    echo -e "${RED}WARNING: This will delete ALL data in Redis!${NC}"
    read -p "Type 'FLUSH' to confirm: " confirm
    if [ "$confirm" = "FLUSH" ]; then
        redis_cmd FLUSHALL
        log_success "Redis flushed."
    else
        log_info "Cancelled."
    fi
}

# Monitor commands in real-time
monitor() {
    log_info "Monitoring Redis commands (Ctrl+C to stop)..."
    docker exec -it "$REDIS_CONTAINER" redis-cli MONITOR
}

# Slow log
slowlog() {
    local count=${1:-10}
    log_info "Last $count slow queries:"
    redis_cmd SLOWLOG GET "$count"
}

# Show help
help() {
    echo "SafeGuard AI - Redis Helper"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Connection:"
    echo "  connect              Open Redis CLI"
    echo "  ping                 Ping Redis"
    echo "  info                 Server info"
    echo ""
    echo "Keys:"
    echo "  count_keys [pattern] Count keys (default: *)"
    echo "  list_keys [pattern]  List keys"
    echo "  get_key [key]        Get key value"
    echo "  delete_key [key]     Delete single key"
    echo "  delete_pattern [p]   Delete by pattern"
    echo ""
    echo "SafeGuard Specific:"
    echo "  idempotency_keys     List idempotency keys"
    echo "  rule_cache           List rule cache"
    echo "  feature_cache        List feature cache"
    echo "  clear_idempotency    Clear idempotency keys"
    echo "  clear_cache          Clear all caches"
    echo ""
    echo "Diagnostics:"
    echo "  memory               Memory analysis"
    echo "  monitor              Monitor commands live"
    echo "  slowlog [n]          Show slow queries"
    echo ""
    echo "Dangerous:"
    echo "  flush_all            Delete ALL data"
    echo ""
    echo "Environment:"
    echo "  REDIS_CONTAINER=$REDIS_CONTAINER"
}

# Main
case "${1:-help}" in
    connect) connect ;;
    ping) ping ;;
    info) info ;;
    count_keys) count_keys "$2" ;;
    list_keys) list_keys "$2" "$3" ;;
    get_key) get_key "$2" ;;
    delete_key) delete_key "$2" ;;
    delete_pattern) delete_pattern "$2" ;;
    idempotency_keys) idempotency_keys ;;
    rule_cache) rule_cache ;;
    feature_cache) feature_cache ;;
    clear_idempotency) clear_idempotency ;;
    clear_cache) clear_cache ;;
    memory) memory ;;
    monitor) monitor ;;
    slowlog) slowlog "$2" ;;
    flush_all) flush_all ;;
    help|*) help ;;
esac
