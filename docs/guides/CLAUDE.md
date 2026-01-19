# FraudGuard AI - Claude Code Configuration

## Project Overview
Real-time fraud detection engine for payment transactions.
- Target latency: <100ms P95
- Fraud detection rate: 94%
- Architecture: Microservices with Python FastAPI

## Tech Stack
- **Language**: Python 3.11
- **API Framework**: FastAPI + Uvicorn
- **ML Model**: LightGBM (binary classification)
- **Databases**: PostgreSQL 16, Redis 7
- **Message Queue**: Kafka 7.6
- **Monitoring**: Prometheus + Grafana
- **Container**: Docker + Docker Compose
- **Orchestration**: Kubernetes (optional)

## Project Structure
```
services/
├── decision-engine/     # Main orchestration (port 8000)
├── model-serving/       # ML inference (port 8001)
├── rules-service/       # Rules evaluation (port 8003)
platform/
├── postgres/migrations/ # Database migrations (Flyway-style)
├── observability/       # Prometheus + Grafana configs
tests/
├── unit/               # Fast unit tests
├── integration/        # Docker-dependent tests
├── e2e/               # Full system tests
```

## Common Commands

### Development
```bash
make up              # Start all services
make down            # Stop services
make logs            # View logs
make health          # Check service health
make migrate         # Run database migrations
```

### Docker Helper Script
```bash
./scripts/docker-helper.sh start      # Start services
./scripts/docker-helper.sh stop       # Stop services
./scripts/docker-helper.sh health     # Health check all services
./scripts/docker-helper.sh logs       # View all logs
./scripts/docker-helper.sh logs decision-engine  # Specific service
./scripts/docker-helper.sh shell      # Shell into container
./scripts/docker-helper.sh migrate    # Run DB migrations
./scripts/docker-helper.sh smoke_test # Quick API test
./scripts/docker-helper.sh stats      # Resource usage
./scripts/docker-helper.sh clean      # Remove volumes/images
./scripts/docker-helper.sh reset      # Full reset
```

### Docker Development Tools (optional)
```bash
# Start with admin tools
docker compose --profile tools up -d

# Access points:
# - pgAdmin: http://localhost:5050 (admin@fraudguard.local / admin)
# - Redis Commander: http://localhost:8081
# - Kafka UI: http://localhost:8082
```

### Testing
```bash
# Run all unit tests
pytest tests/unit -v

# Run with coverage
pytest tests/unit --cov=services --cov-report=html

# Run integration tests (requires Docker)
make up
pytest tests/integration -m integration

# Run specific test file
pytest tests/unit/test_model_serving.py -v

# Run tests matching pattern
pytest -k "test_decision" -v
```

### Code Quality
```bash
# Lint with ruff
ruff check services/

# Format with black
black services/

# Type check
mypy services/
```

## API Endpoints

### Decision Engine (8000)
- `POST /v1/score` - Main fraud scoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Model Serving (8001)
- `POST /predict` - ML prediction
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Rules Service (8003)
- `POST /evaluate` - Rule evaluation
- `GET /health` - Health check

## Testing Guidelines

### Test Markers
- `@pytest.mark.unit` - Fast unit tests (no external deps)
- `@pytest.mark.integration` - Require Docker services
- `@pytest.mark.e2e` - Full system tests
- `@pytest.mark.model` - ML model tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.database` - PostgreSQL tests
- `@pytest.mark.redis` - Redis tests

### Fixtures Available
- `sample_transaction` - Normal transaction
- `high_risk_transaction` - Fraudulent pattern
- `low_risk_transaction` - Safe transaction
- `mock_redis_client` - Redis mock
- `mock_db_pool` - PostgreSQL mock

## Decision Logic
```
Score < 0.50         → ALLOW
0.50 ≤ Score ≤ 0.70  → CHALLENGE (2FA)
Score > 0.70         → DENY

Override conditions:
- Deny list match   → DENY
- Critical rule     → DENY
- Allow list match  → May reduce friction
```

## Feature Engineering (12 features)
1. `amt` - Transaction amount
2. `trans_hour` - Hour (0-23)
3. `trans_day` - Day of week (0=Monday)
4. `merchant_mcc` - Merchant category code
5. `card_type` - 0=physical, 1=virtual
6. `channel` - 0=app, 1=web, 2=pos, 3=atm
7. `is_international` - 0/1
8. `is_night` - 0/1 (23:00-05:00)
9. `is_weekend` - 0/1
10. `amount_category` - 0-3 (bucketed)
11. `distance_category` - 0-3 (km from user)
12. `city_pop` - City population

## Environment Variables
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=antifraud
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_dev

REDIS_HOST=localhost
REDIS_PORT=6379

KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ENABLE=true

MODEL_SERVING_URL=http://localhost:8001
RULES_SERVICE_URL=http://localhost:8003
```

## Database Schema (Key Tables)
- `events` - Transaction events (immutable)
- `decisions` - Fraud decisions with audit
- `rules` - Versioned rule definitions
- `lists` - Allow/deny lists
- `cases` - Analyst investigations
- `labels` - Ground truth for retraining

## Code Style
- Use async/await for I/O operations
- Type hints required (mypy strict)
- Docstrings for public functions
- Max line length: 100 characters
- Import order: stdlib, third-party, local

## CI/CD Pipeline

### GitHub Actions Workflows
- `.github/workflows/ci.yml` - Main CI (lint, test, build)
- `.github/workflows/cd.yml` - Deployment pipeline
- `.github/workflows/pr-checks.yml` - PR validation

### CI Jobs
1. **lint** - Ruff, Black, isort checks
2. **unit-tests** - pytest with coverage
3. **integration-tests** - With PostgreSQL/Redis services
4. **security** - Bandit + Safety scanning
5. **build** - Docker image build
6. **type-check** - mypy validation

### Deployment
```bash
# Tag for release
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# Manual deploy to staging
gh workflow run cd.yml -f environment=staging

# Deploy to production (requires approval)
gh workflow run cd.yml -f environment=production
```

### Commit Convention
Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `ci:` - CI/CD changes
- `chore:` - Maintenance

## Helper Scripts

All scripts are in `scripts/` directory:

```bash
# Docker management
./scripts/docker-helper.sh help

# Database operations
./scripts/db-helper.sh help

# Kubernetes deployment
./scripts/k8s-helper.sh help

# Kafka management
./scripts/kafka-helper.sh help

# Redis management
./scripts/redis-helper.sh help

# ML model testing
./scripts/ml-helper.sh help
```

## Security Notes
- Never log full card numbers (use tokens)
- Hash IP addresses in logs
- Immutable audit trail required
- GDPR: 90-day online retention
- PSD2: SCA/2FA integration
