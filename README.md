# Antifraud Engine

Real-time fraud detection engine for card payments with ML-powered scoring and rule-based decision making.

## Architecture

- **Decision Engine**: Core orchestrator (FastAPI/Python)
- **Model Serving**: ML inference service (LightGBM/XGBoost)
- **Rules Service**: Rule engine for business logic
- **Feature Store**: Redis for online features
- **OLTP Database**: PostgreSQL for transactional data
- **Event Bus**: Kafka for async processing
- **Observability**: Prometheus + Grafana

## Performance Targets

- **P95 Latency**: < 100ms
- **Throughput**: 3-10k TPS
- **Availability**: 99.95%
- **False Positive Rate**: < 2%

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Make

### 1. Clone and Setup

```bash
git clone <repo-url>
cd bank-security
cp .env.example .env
```

### 2. Start Infrastructure

```bash
make up
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Kafka (port 9092)
- Prometheus (port 9090)
- Grafana (port 3000)

### 3. Run Migrations

```bash
make migrate
```

### 4. Check Health

```bash
make health
```

### 5. Access Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## API Usage

### Score Transaction

```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "bank-001",
    "idempotency_key": "tx-12345-20250930",
    "event": {
      "type": "card_payment",
      "id": "evt_12345",
      "ts": "2025-09-30T15:30:00Z",
      "amount": 150.00,
      "currency": "EUR",
      "merchant": {
        "id": "merch_789",
        "name": "Online Store",
        "mcc": "5411",
        "country": "FR"
      },
      "card": {
        "card_id": "card_abc123",
        "type": "physical",
        "user_id": "user_xyz"
      },
      "context": {
        "ip": "192.168.1.1",
        "geo": "FR",
        "device_id": "dev_12345",
        "channel": "app"
      }
    }
  }'
```

### Response

```json
{
  "decision_id": "dec_67890",
  "decision": "ALLOW",
  "score": 0.12,
  "rule_hits": [],
  "reasons": [],
  "latency_ms": 45,
  "model_version": "gbdt_v1"
}
```

## Project Structure

```
.
├── artifacts/          # Models, rules, lists
├── deploy/            # Kubernetes manifests
├── docs/              # Documentation & API specs
├── platform/          # Infrastructure configs
├── services/          # Microservices
│   ├── decision-engine/
│   ├── model-serving/
│   ├── rules-service/
│   └── case-service/
└── tests/             # Tests
```

## Development

### View Logs

```bash
make logs
```

### Run Tests

```bash
make test
```

### Stop Services

```bash
make down
```

## Roadmap

### MVP (Current Phase)
- [x] Repository structure
- [x] Docker Compose setup
- [x] API schema definition
- [ ] Database migrations
- [ ] Model serving service
- [ ] Decision engine
- [ ] Feature engineering
- [ ] Basic rules engine

### V1
- [ ] Case management UI
- [ ] Advanced explainability
- [ ] Model canary deployment
- [ ] Drift detection
- [ ] Load testing validation

## Security & Compliance

- PII minimization (no PAN, tokenized IDs)
- Audit logs with signatures
- GDPR compliant (data retention policies)
- mTLS for internal communication (production)

## Support

For issues or questions, contact the security team.

## License

Proprietary - Internal use only
