.PHONY: help up down logs ps migrate health test clean setup demo
.PHONY: db-migrate db-reset db-stats db-connect
.PHONY: kafka-list kafka-consume redis-flush
.PHONY: ml-train ml-test ml-list
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help:
	@echo "$(BLUE)FraudGuard - Available Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Docker Commands:$(NC)"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - Show logs (all services)"
	@echo "  make logs-[service] - Show logs for specific service (e.g., make logs-decision)"
	@echo "  make ps             - Show container status"
	@echo "  make rebuild        - Rebuild all services"
	@echo "  make clean          - Clean containers, volumes, images"
	@echo ""
	@echo "$(GREEN)Database Commands:$(NC)"
	@echo "  make db-migrate     - Run database migrations"
	@echo "  make db-reset       - Reset database (DROP + migrations)"
	@echo "  make db-stats       - Show database statistics"
	@echo "  make db-connect     - Connect to PostgreSQL CLI"
	@echo ""
	@echo "$(GREEN)Kafka Commands:$(NC)"
	@echo "  make kafka-list     - List all Kafka topics"
	@echo "  make kafka-consume  - Consume fraud-events topic"
	@echo ""
	@echo "$(GREEN)Redis Commands:$(NC)"
	@echo "  make redis-info     - Show Redis server info"
	@echo "  make redis-flush    - Flush Redis cache"
	@echo "  make redis-connect  - Connect to Redis CLI"
	@echo ""
	@echo "$(GREEN)ML Model Commands:$(NC)"
	@echo "  make ml-train       - Train fraud detection model"
	@echo "  make ml-test        - Test model prediction"
	@echo "  make ml-list        - List available models"
	@echo ""
	@echo "$(GREEN)Health & Testing:$(NC)"
	@echo "  make health         - Check health of all services"
	@echo "  make test           - Run unit tests"
	@echo "  make test-e2e       - Run end-to-end tests"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make setup          - Initial setup (up + migrate + health)"
	@echo "  make check          - Check setup status"

# ==================== Docker Commands ====================

up:
	@echo "$(BLUE)[INFO]$(NC) Starting all services..."
	docker compose up -d
	@echo "$(GREEN)[SUCCESS]$(NC) Services started. Run 'make ps' to check status."

down:
	@echo "$(BLUE)[INFO]$(NC) Stopping all services..."
	docker compose down
	@echo "$(GREEN)[SUCCESS]$(NC) Services stopped."

restart: down up

logs:
	docker compose logs -f --tail=200

logs-decision:
	docker compose logs -f decision-engine

logs-model:
	docker compose logs -f model-serving

logs-rules:
	docker compose logs -f rules-service

logs-case:
	docker compose logs -f case-service

ps:
	docker compose ps

rebuild:
	@echo "$(BLUE)[INFO]$(NC) Rebuilding all services..."
	docker compose up -d --build
	@echo "$(GREEN)[SUCCESS]$(NC) Services rebuilt."

clean:
	@echo "$(YELLOW)[WARN]$(NC) Cleaning containers, volumes, and images..."
	docker compose down -v
	docker system prune -f
	@echo "$(GREEN)[SUCCESS]$(NC) Cleanup complete."

# ==================== Database Commands ====================

db-migrate:
	@echo "$(BLUE)[INFO]$(NC) Running database migrations..."
	@./scripts/db-helper.sh migrate

db-reset:
	@echo "$(YELLOW)[WARN]$(NC) Resetting database..."
	@./scripts/db-helper.sh reset

db-stats:
	@./scripts/db-helper.sh stats

db-connect:
	@./scripts/db-helper.sh connect

# ==================== Kafka Commands ====================

kafka-list:
	@./scripts/kafka-helper.sh list

kafka-consume:
	@./scripts/kafka-helper.sh consume fraud-events

# ==================== Redis Commands ====================

redis-info:
	@./scripts/redis-helper.sh info

redis-flush:
	@./scripts/redis-helper.sh flush

redis-connect:
	@./scripts/redis-helper.sh connect

# ==================== ML Model Commands ====================

ml-train:
	@echo "$(BLUE)[INFO]$(NC) Training fraud detection model..."
	python scripts/train_fraud_model_kaggle.py

ml-test:
	@./scripts/ml-helper.sh test

ml-list:
	@./scripts/ml-helper.sh list

# ==================== Health & Testing ====================

health:
	@echo "$(BLUE)[INFO]$(NC) Checking service health..."
	@echo -n "PostgreSQL: "
	@docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Redis: "
	@docker compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Kafka: "
	@docker compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Prometheus: "
	@curl -s http://localhost:9090/-/healthy > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Grafana: "
	@curl -s http://localhost:3000/api/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Decision Engine: "
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Model Serving: "
	@curl -s http://localhost:8001/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"
	@echo -n "Rules Service: "
	@curl -s http://localhost:8003/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ DOWN"

test:
	@echo "$(BLUE)[INFO]$(NC) Running unit tests..."
	pytest tests/unit/ -v

test-e2e:
	@echo "$(BLUE)[INFO]$(NC) Running end-to-end tests..."
	pytest tests/e2e/ -v

# ==================== Setup ====================

check:
	@./check-setup.sh


# ==================== Two-Command UX ====================

setup:
	docker compose up -d
	@echo "Waiting for services to start..."
	sleep 10
	./scripts/db-helper.sh migrate
	@echo "Setup complete! Access:"
	@echo "  - API: http://localhost:8000"
	@echo "  - Grafana: http://localhost:3000"

demo:
	@echo "Running demo transaction..."
	curl -X POST http://localhost:8000/v1/score \\
	  -H "Content-Type: application/json" \\
	  -d '{"event_id":"demo-001","amount":9500,"currency":"EUR","merchant":{"id":"m1","name":"CryptoExchange","mcc":"6211","country":"RU"},"card":{"card_id":"c1","user_id":"u1","type":"virtual"},"context":{"ip":"185.220.101.1","channel":"web"}}'
