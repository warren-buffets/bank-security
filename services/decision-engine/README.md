# Decision Engine Service

The **Decision Engine** is the orchestration service for SafeGuard AI's real-time fraud detection system. It coordinates parallel calls to the Model Serving and Rules Service to make fraud decisions in under 100ms.

## Overview

The Decision Engine:
- Receives transaction scoring requests via POST `/v1/score`
- Checks idempotency using Redis (prevents duplicate processing)
- Orchestrates parallel calls to:
  - **Model Serving**: ML-based risk scoring (LightGBM/XGBoost)
  - **Rules Service**: Business rule evaluation
- Makes final decision: **ALLOW**, **CHALLENGE**, or **DENY**
- Stores events and decisions in PostgreSQL
- Publishes decision events to Kafka
- Returns response with score, reasons, and latency metrics

## Architecture

```
Client Request
      |
      v
+---------------------+
| Idempotency Check   | <--- Redis
+---------------------+
      |
      v
+---------------------+
| Store Event         | ---> PostgreSQL (events table)
+---------------------+
      |
      v
+---------------------+
| Parallel Calls:     |
| - Model Serving     | <--- ML Score (20ms budget)
| - Rules Service     | <--- Rule Evaluation (30ms budget)
+---------------------+
      |
      v
+---------------------+
| Decision Logic      | (15ms budget)
+---------------------+
      |
      v
+---------------------+
| Store Decision      | ---> PostgreSQL (decisions table)
+---------------------+
      |
      v
+---------------------+
| Publish to Kafka    | ---> decision_events, case_events
+---------------------+
      |
      v
Response (P95 < 100ms)
```

## Decision Logic

The service implements intelligent decision logic:

1. **Critical Rules** → DENY (overrides everything)
2. **Score > 0.70** → CHALLENGE or DENY (high risk)
3. **Score 0.50-0.70 + No 2FA** → CHALLENGE (request 2FA)
4. **Score 0.50-0.70 + Has 2FA** → ALLOW (2FA sufficient)
5. **Score < 0.50** → ALLOW (low risk)
6. **ML Failed** → CHALLENGE (fail-safe)

## API Endpoints

### POST /v1/score

Score a transaction and make a fraud decision.

**Request:**
```json
{
  "event_id": "evt_abc123",
  "tenant_id": "bank_fr",
  "amount": 150.00,
  "currency": "EUR",
  "merchant": {
    "id": "mch_xyz789",
    "name": "Amazon FR",
    "mcc": "5411",
    "country": "FR"
  },
  "card": {
    "card_id": "card_456",
    "user_id": "user_789",
    "type": "physical"
  },
  "context": {
    "ip": "92.168.1.1",
    "geo": "FR",
    "device_id": "dev_123",
    "channel": "app"
  },
  "has_initial_2fa": false
}
```

**Response:**
```json
{
  "event_id": "evt_abc123",
  "decision_id": "dec_xyz456",
  "decision": "ALLOW",
  "score": 0.23,
  "reasons": ["Low risk score", "Known device"],
  "rule_hits": [],
  "latency_ms": 87,
  "model_version": "v1.0.0",
  "requires_2fa": false
}
```

### GET /health

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "decision-engine",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "dependencies": {
    "redis": "healthy",
    "postgres": "healthy",
    "kafka": "healthy"
  }
}
```

### GET /metrics

Prometheus metrics endpoint.

Returns metrics including:
- `decision_engine_requests_total` - Total requests
- `decision_engine_decisions_total` - Decisions by type
- `decision_engine_latency_seconds` - Request latency histogram
- `decision_engine_scores` - ML score distribution

## Configuration

Environment variables (see `.env.example`):

```bash
# Service
SERVICE_NAME=decision-engine
VERSION=1.0.0
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# External services
MODEL_SERVING_URL=http://model-serving:8001
RULES_SERVICE_URL=http://rules-service:8002

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=safeguard
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ENABLE=true

# Model
MODEL_VERSION=v1.0.0

# Thresholds
THRESHOLD_LOW_RISK=0.50
THRESHOLD_HIGH_RISK=0.70
```

## Running Locally

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis
- Kafka (optional, can be disabled)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Service
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using Docker
```bash
# Build
docker build -t decision-engine:latest .

# Run
docker run -p 8000:8000 \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  -e KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
  decision-engine:latest
```

## Performance Targets

- **P95 Latency**: < 100ms (total)
- **P95 Orchestration**: < 15ms (decision logic)
- **Throughput**: 10k TPS (horizontally scalable)
- **Availability**: 99.95%

### Latency Budget Breakdown

| Component | Budget | Notes |
|-----------|--------|-------|
| Orchestration | 15ms | Decision logic, aggregation |
| Model Serving | 30ms | ML inference |
| Rules Service | 50ms | Rule evaluation + Redis |
| Redis queries | 5ms | Idempotency, features |
| PostgreSQL | 10ms | Event/decision storage |

## Features

- **Idempotency**: Redis-backed idempotency checks (24h TTL)
- **Parallel Execution**: Model and Rules called simultaneously
- **Fail-Safe**: Graceful degradation if services unavailable
- **Event Sourcing**: All events stored immutably
- **Audit Trail**: All decisions tracked with reasons
- **Metrics**: Prometheus metrics for monitoring
- **Health Checks**: Dependency health reporting
- **2FA Intelligence**: Reuses existing 2FA, requests only when needed

## Monitoring

### Key Metrics
- Decision latency (P50, P95, P99)
- Decision distribution (ALLOW/CHALLENGE/DENY)
- ML score distribution
- Error rates by endpoint
- Dependency health

### Logs
Structured JSON logs with:
- Request ID
- Decision details
- Latency breakdown
- Error traces

## Testing

### Example Request (curl)
```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test_123",
    "amount": 100.0,
    "currency": "EUR",
    "merchant": {
      "id": "mch_1",
      "mcc": "5411",
      "country": "FR"
    },
    "card": {
      "card_id": "card_1",
      "user_id": "user_1",
      "type": "physical"
    },
    "context": {
      "channel": "app",
      "geo": "FR"
    }
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Deployment

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: decision-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: decision-engine
  template:
    metadata:
      labels:
        app: decision-engine
    spec:
      containers:
      - name: decision-engine
        image: decision-engine:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_HOST
          value: postgres-service
        - name: REDIS_HOST
          value: redis-service
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka-service:9092
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## License

Proprietary - SafeGuard AI
