#!/bin/bash
# FraudGuard AI - Kafka Helper Script
# Usage: ./scripts/kafka-helper.sh [command]

set -e

KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
KAFKA_CONTAINER="${KAFKA_CONTAINER:-antifraud-kafka}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# List topics
list_topics() {
    log_info "Listing Kafka topics..."
    docker exec "$KAFKA_CONTAINER" kafka-topics --bootstrap-server kafka:29092 --list
}

# Create topic
create_topic() {
    local topic=$1
    local partitions=${2:-3}
    local replication=${3:-1}

    log_info "Creating topic: $topic (partitions: $partitions, replication: $replication)"
    docker exec "$KAFKA_CONTAINER" kafka-topics --bootstrap-server kafka:29092 \
        --create --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor "$replication" \
        2>/dev/null || log_info "Topic may already exist"
}

# Describe topic
describe_topic() {
    local topic=$1
    log_info "Describing topic: $topic"
    docker exec "$KAFKA_CONTAINER" kafka-topics --bootstrap-server kafka:29092 \
        --describe --topic "$topic"
}

# Delete topic
delete_topic() {
    local topic=$1
    log_info "Deleting topic: $topic"
    docker exec "$KAFKA_CONTAINER" kafka-topics --bootstrap-server kafka:29092 \
        --delete --topic "$topic"
}

# Consume messages
consume() {
    local topic=${1:-decision_events}
    local count=${2:-10}
    log_info "Consuming $count messages from $topic..."
    docker exec "$KAFKA_CONTAINER" kafka-console-consumer --bootstrap-server kafka:29092 \
        --topic "$topic" \
        --from-beginning \
        --max-messages "$count"
}

# Produce test message
produce() {
    local topic=${1:-decision_events}
    local message=${2:-'{"test": "message"}'}
    log_info "Producing message to $topic..."
    echo "$message" | docker exec -i "$KAFKA_CONTAINER" kafka-console-producer \
        --bootstrap-server kafka:29092 \
        --topic "$topic"
    log_success "Message sent."
}

# Consumer groups
consumer_groups() {
    log_info "Listing consumer groups..."
    docker exec "$KAFKA_CONTAINER" kafka-consumer-groups --bootstrap-server kafka:29092 --list
}

# Consumer group lag
consumer_lag() {
    local group=$1
    log_info "Consumer lag for group: $group"
    docker exec "$KAFKA_CONTAINER" kafka-consumer-groups --bootstrap-server kafka:29092 \
        --describe --group "$group"
}

# Setup FraudGuard topics
setup_topics() {
    log_info "Setting up FraudGuard Kafka topics..."
    create_topic "decision_events" 3 1
    create_topic "case_events" 3 1
    create_topic "audit_events" 3 1
    create_topic "model_predictions" 3 1
    log_success "Topics created."
}

# Show help
help() {
    echo "FraudGuard AI - Kafka Helper"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Topics:"
    echo "  list_topics              List all topics"
    echo "  create_topic [name] [p]  Create topic (default 3 partitions)"
    echo "  describe_topic [name]    Describe topic"
    echo "  delete_topic [name]      Delete topic"
    echo "  setup_topics             Create all FraudGuard topics"
    echo ""
    echo "Messages:"
    echo "  consume [topic] [n]      Consume n messages (default: 10)"
    echo "  produce [topic] [msg]    Produce message"
    echo ""
    echo "Consumer Groups:"
    echo "  consumer_groups          List consumer groups"
    echo "  consumer_lag [group]     Show consumer lag"
    echo ""
    echo "Environment:"
    echo "  KAFKA_CONTAINER=$KAFKA_CONTAINER"
}

# Main
case "${1:-help}" in
    list_topics) list_topics ;;
    create_topic) create_topic "$2" "$3" "$4" ;;
    describe_topic) describe_topic "$2" ;;
    delete_topic) delete_topic "$2" ;;
    setup_topics) setup_topics ;;
    consume) consume "$2" "$3" ;;
    produce) produce "$2" "$3" ;;
    consumer_groups) consumer_groups ;;
    consumer_lag) consumer_lag "$2" ;;
    help|*) help ;;
esac
