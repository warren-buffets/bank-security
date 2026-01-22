#!/bin/bash
# FraudGuard AI - Docker Helper Script
# Usage: ./scripts/docker-helper.sh [command]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Start all services
start() {
    log_info "Starting all services..."
    docker compose up -d
    log_success "Services started. Run 'docker compose ps' to check status."
}

# Stop all services
stop() {
    log_info "Stopping all services..."
    docker compose down
    log_success "Services stopped."
}

# Restart all services
restart() {
    stop
    start
}

# View logs
logs() {
    local service=${1:-}
    if [ -n "$service" ]; then
        docker compose logs -f "$service"
    else
        docker compose logs -f
    fi
}

# Check health of all services
health() {
    log_info "Checking service health..."
    echo ""

    # Infrastructure services
    echo "=== Infrastructure ==="
    curl -s http://localhost:5432 >/dev/null 2>&1 && echo -e "PostgreSQL: ${GREEN}UP${NC}" || echo -e "PostgreSQL: ${RED}DOWN${NC}"
    curl -s http://localhost:6379 >/dev/null 2>&1 && echo -e "Redis: ${GREEN}UP${NC}" || echo -e "Redis: ${RED}DOWN${NC}"
    curl -s http://localhost:9092 >/dev/null 2>&1 && echo -e "Kafka: ${GREEN}UP${NC}" || echo -e "Kafka: ${YELLOW}CHECK${NC}"
    echo ""

    # Application services
    echo "=== Application Services ==="
    check_service "Decision Engine" "http://localhost:8000/health"
    check_service "Model Serving" "http://localhost:8001/health"
    check_service "Rules Service" "http://localhost:8003/health"
    echo ""

    # Monitoring
    echo "=== Monitoring ==="
    check_service "Prometheus" "http://localhost:9090/-/healthy"
    check_service "Grafana" "http://localhost:3000/api/health"
}

check_service() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$response" = "200" ]; then
        echo -e "$name: ${GREEN}HEALTHY${NC}"
    else
        echo -e "$name: ${RED}UNHEALTHY (HTTP $response)${NC}"
    fi
}

# Build all images
build() {
    log_info "Building all Docker images..."
    docker compose build --no-cache
    log_success "Build complete."
}

# Build specific service
build_service() {
    local service=$1
    if [ -z "$service" ]; then
        log_error "Please specify a service: decision-engine, model-serving, rules-service"
        exit 1
    fi
    log_info "Building $service..."
    docker compose build --no-cache "$service"
    log_success "$service built."
}

# Run database migrations
migrate() {
    log_info "Running database migrations..."
    docker compose exec -T postgres sh -c '
        for f in /migrations/*.sql; do
            echo "Running $f..."
            psql -U postgres -d antifraud -f "$f" 2>/dev/null || true
        done
    '
    log_success "Migrations complete."
}

# Shell into a container
shell() {
    local service=${1:-decision-engine}
    log_info "Opening shell in $service..."
    docker compose exec "$service" /bin/sh
}

# Clean up volumes and images
clean() {
    log_warn "This will remove all containers, volumes, and images for this project."
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose down -v --rmi local
        log_success "Cleanup complete."
    else
        log_info "Cleanup cancelled."
    fi
}

# Show resource usage
stats() {
    docker stats --no-stream $(docker compose ps -q)
}

# Run a quick smoke test
smoke_test() {
    log_info "Running smoke test..."

    # Test decision engine
    log_info "Testing Decision Engine..."
    curl -s -X POST http://localhost:8000/v1/score \
        -H "Content-Type: application/json" \
        -d '{
            "event_id": "smoke_test_001",
            "idempotency_key": "smoke_'$(date +%s)'",
            "amount": 100.00,
            "currency": "EUR",
            "card_id": "card_smoke",
            "merchant_id": "merch_test",
            "merchant_mcc": "5411",
            "channel": "pos",
            "card_type": "physical"
        }' | jq .

    log_success "Smoke test complete."
}

# Reset everything (for fresh start)
reset() {
    log_warn "This will reset all data and start fresh."
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        clean
        start
        sleep 10
        migrate
        log_success "Reset complete."
    fi
}

# Show help
help() {
    echo "FraudGuard AI - Docker Helper"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  logs [service]  View logs (optionally for specific service)"
    echo "  health          Check health of all services"
    echo "  build           Build all Docker images"
    echo "  build_service   Build specific service"
    echo "  migrate         Run database migrations"
    echo "  shell [service] Open shell in container (default: decision-engine)"
    echo "  stats           Show resource usage"
    echo "  smoke_test      Run quick smoke test"
    echo "  clean           Remove all containers, volumes, images"
    echo "  reset           Full reset (clean + start + migrate)"
    echo "  help            Show this help"
}

# Main entry point
case "${1:-help}" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    logs) logs "$2" ;;
    health) health ;;
    build) build ;;
    build_service) build_service "$2" ;;
    migrate) migrate ;;
    shell) shell "$2" ;;
    stats) stats ;;
    smoke_test) smoke_test ;;
    clean) clean ;;
    reset) reset ;;
    help|*) help ;;
esac
