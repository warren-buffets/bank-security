# FraudGuard AI - Rules Service

High-performance rules evaluation service for fraud detection in banking transactions.

## Overview

The Rules Service evaluates transactions against configurable fraud detection rules and deny/allow lists. It supports a custom DSL (Domain Specific Language) for rule expressions and provides sub-50ms evaluation times.

## Features

- **Fast Rule Evaluation**: Sub-50ms response time with timeout enforcement
- **Custom DSL**: Powerful expression language for fraud rules
- **Deny/Allow Lists**: Redis-cached lists for instant blocking/whitelisting
- **Database-Backed Rules**: PostgreSQL storage with caching
- **Prometheus Metrics**: Built-in monitoring and observability
- **Production Ready**: Health checks, logging, error handling

## Architecture

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       v
┌─────────────────┐
│  FastAPI App    │
└──────┬──────────┘
       │
       ├─────────> Lists Checker (Redis)
       │           - Deny lists
       │           - Allow lists
       │
       └─────────> Rules Engine
                   - Load rules (PostgreSQL)
                   - DSL evaluation
                   - Priority ordering
```

## DSL Syntax

The Rules Service supports a powerful DSL for rule expressions:

### Operators

- **Comparisons**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **Logical**: `AND`, `OR`, `NOT`
- **Membership**: `IN`

### Functions

- `velocity_24h('amount')` - Sum of amounts in last 24 hours
- `velocity_24h('count')` - Transaction count in last 24 hours
- `velocity_1h('count')` - Transaction count in last 1 hour

### Example Rules

```python
# High amount transaction
"amount > 1000"

# Foreign transaction
"geo != user_home_geo"

# Combined rule
"amount > 1000 AND geo != user_home_geo"

# High-risk merchant category
"merchant_category IN ['gambling', 'crypto', 'forex']"

# Velocity check
"velocity_24h('amount') > 5000"

# Complex rule
"amount > 500 AND (geo != user_home_geo OR merchant_category IN ['gambling']) AND velocity_24h('count') > 3"
```

## API Endpoints

### POST /evaluate

Evaluate a transaction against fraud rules.

**Request:**
```json
{
  "context": {
    "transaction_id": "tx_123456",
    "user_id": "user_789",
    "amount": 1500.00,
    "currency": "USD",
    "merchant_id": "merch_456",
    "merchant_category": "electronics",
    "geo": "RU",
    "user_home_geo": "US",
    "ip_address": "192.168.1.1",
    "device_id": "dev_abc",
    "payment_method": "credit_card",
    "tx_count_24h": 3,
    "amount_sum_24h": 2500.00
  },
  "check_lists": true
}
```

**Response:**
```json
{
  "transaction_id": "tx_123456",
  "should_deny": true,
  "should_review": false,
  "matched_rules": [
    {
      "rule_id": "rule_001",
      "rule_name": "High Amount Foreign Transaction",
      "expression": "amount > 1000 AND geo != user_home_geo",
      "action": "deny",
      "reason": "Large transaction from foreign country",
      "priority": 10,
      "metadata": {}
    }
  ],
  "list_matches": [],
  "evaluation_time_ms": 12.5,
  "reasons": ["Large transaction from foreign country"]
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "rules-service",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "postgresql": "healthy",
    "redis": "healthy"
  }
}
```

### GET /rules

List all active rules.

### POST /rules/reload

Reload rules from database (admin endpoint).

### GET /metrics

Prometheus metrics endpoint.

## Configuration

Environment variables:

```bash
# Service
HOST=0.0.0.0
PORT=8003
LOG_LEVEL=INFO

# Timeouts
EVALUATION_TIMEOUT_MS=50

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fraudguard
POSTGRES_USER=fraudguard
POSTGRES_PASSWORD=fraudguard

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Cache
RULES_CACHE_TTL=300
LISTS_CACHE_TTL=600

# Metrics
METRICS_ENABLED=true
```

## Database Schema

### Rules Table

```sql
CREATE TABLE rules (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    action VARCHAR(50) NOT NULL,  -- deny, review, allow
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rules_enabled ON rules(enabled);
CREATE INDEX idx_rules_priority ON rules(priority DESC);
```

## Redis Lists

### Deny Lists
- `deny_list:user_id` - Set of denied user IDs
- `deny_list:ip_address` - Set of denied IP addresses
- `deny_list:device_id` - Set of denied device IDs
- `deny_list:merchant_id` - Set of denied merchant IDs
- `deny_list:geo` - Set of denied countries/regions

### Allow Lists
- `allow_list:user_id` - Set of whitelisted user IDs
- `allow_list:ip_address` - Set of whitelisted IP addresses
- `allow_list:device_id` - Set of whitelisted device IDs

## Running the Service

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m uvicorn app.main:app --reload --port 8003
```

### Docker

```bash
# Build image
docker build -t rules-service:latest .

# Run container
docker run -p 8003:8003 \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  rules-service:latest
```

### Docker Compose

```yaml
services:
  rules-service:
    build: .
    ports:
      - "8003:8003"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
```

## Testing

### Example: Add to Deny List

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

# Deny a user
r.sadd('deny_list:user_id', 'user_123')

# Deny an IP address
r.sadd('deny_list:ip_address', '192.168.1.100')
```

### Example: Create a Rule

```sql
INSERT INTO rules (id, name, expression, action, priority, enabled, description)
VALUES (
    'rule_high_amount',
    'High Amount Transaction',
    'amount > 1000',
    'review',
    10,
    true,
    'Flag transactions over $1000 for review'
);
```

### Example: Test Evaluation

```bash
curl -X POST http://localhost:8003/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "transaction_id": "tx_123",
      "user_id": "user_456",
      "amount": 1500.00,
      "geo": "US",
      "user_home_geo": "US"
    }
  }'
```

## Performance

- **Target**: <50ms evaluation time
- **Timeout**: Configurable (default 50ms)
- **Throughput**: 1000+ req/s (single instance)
- **Caching**: Rules cached for 5 minutes
- **Connection Pooling**: PostgreSQL and Redis

## Metrics

Available Prometheus metrics:

- `rules_evaluations_total{status}` - Counter of evaluations by status
- `rules_evaluation_duration_seconds` - Histogram of evaluation times
- `rules_matched_total{rule_id,action}` - Counter of rule matches
- `list_matches_total{list_type}` - Counter of list matches

## Error Handling

- **Database Connection**: Falls back to cached rules
- **Redis Connection**: Continues without list checks
- **Timeout**: Returns partial results if timeout exceeded
- **Invalid Rules**: Skips and logs invalid rule expressions

## Security

- Non-root container user
- Input validation via Pydantic
- SQL injection protection (parameterized queries)
- No sensitive data in logs

## Development

### Project Structure

```
rules-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── rules_engine.py      # DSL evaluator
│   └── lists_checker.py     # Deny/allow lists
├── Dockerfile
├── requirements.txt
└── README.md
```

### Adding New Rule Functions

Edit `rules_engine.py` and add to `_evaluate_function`:

```python
def _evaluate_function(self, func_name: str, args: List[str], context: Dict[str, Any]) -> Any:
    if func_name == 'my_function':
        # Your logic here
        return result
```

## License

Copyright (c) 2024 FraudGuard AI
