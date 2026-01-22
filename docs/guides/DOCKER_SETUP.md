# FraudGuard AI - Docker Setup Guide

This guide will help you quickly set up and run the FraudGuard AI system using Docker.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- At least 8GB of RAM available for Docker
- At least 10GB of disk space

## Quick Start

### 1. Initial Setup

Copy the environment template:
```bash
cp .env.example .env
```

### 2. Start All Services

```bash
make up
```

This will start:
- **Infrastructure**: PostgreSQL, Redis, Kafka, Zookeeper, Prometheus, Grafana
- **Microservices**: Decision Engine, Model Serving, Rules Service

### 3. Check Service Health

```bash
make health
```

Wait until all services show as HEALTHY before proceeding.

### 4. Test the System

Run a test transaction:
```bash
make test
```

## Service URLs

Once running, you can access:

| Service | URL | Credentials |
|---------|-----|-------------|
| Decision Engine | http://localhost:8000 | - |
| Model Serving | http://localhost:8001 | - |
| Rules Service | http://localhost:8003 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| PostgreSQL | localhost:5432 | fraudguard/fraudguard |
| Redis | localhost:6379 | password: fraudguard |
| Kafka | localhost:9092 | - |

## Available Make Commands

### Core Commands
- `make up` - Start all services
- `make down` - Stop all services
- `make build` - Build all service images
- `make rebuild` - Rebuild and restart everything
- `make restart` - Restart all services

### Monitoring
- `make logs` - Show logs (follow mode)
- `make health` - Check health of all services
- `make ps` - Show running containers

### Testing
- `make test` - Run a test transaction

### Utilities
- `make clean` - Clean up volumes and images
- `make kafka-topics` - List Kafka topics
- `make prometheus-ui` - Open Prometheus
- `make grafana-ui` - Open Grafana
- `make shell-postgres` - Open PostgreSQL shell
- `make shell-redis` - Open Redis CLI

## Architecture Overview

### Infrastructure Services

1. **PostgreSQL** (port 5432)
   - Main database for storing decisions, rules, and audit logs
   - Auto-runs migrations on startup from 

2. **Redis** (port 6379)
   - Caching layer for rules and idempotency checks
   - Session storage

3. **Kafka** (port 9092)
   - Event streaming for decision events and case creation
   - Auto-creates topics on demand

4. **Prometheus** (port 9090)
   - Metrics collection and monitoring
   - Scrapes all microservices

5. **Grafana** (port 3000)
   - Visualization and dashboards
   - Pre-configured with Prometheus datasource

### Microservices

1. **Decision Engine** (port 8000)
   - Main orchestrator for fraud detection
   - Coordinates model serving and rules evaluation
   - Publishes events to Kafka
   - Dependencies: postgres, redis, kafka, model-serving, rules-service

2. **Model Serving** (port 8001)
   - ML model inference service
   - Loads GBDT model from 
   - No external dependencies

3. **Rules Service** (port 8003)
   - Business rules evaluation
   - Manages deny lists and allow lists
   - Dependencies: postgres, redis

## Service Dependencies

The services start in this order (managed by docker-compose):
1. PostgreSQL, Redis, Zookeeper
2. Kafka (depends on Zookeeper)
3. Prometheus
4. Grafana (depends on Prometheus)
5. Model Serving (no dependencies)
6. Rules Service (depends on postgres, redis)
7. Decision Engine (depends on all infrastructure + model-serving + rules-service)

## Networking

All services communicate on the `fraudguard-network` bridge network.

Internal service-to-service URLs:
- `postgres:5432`
- `redis:6379`
- `kafka:29092` (internal) or `localhost:9092` (external)
- `model-serving:8001`
- `rules-service:8003`
- `decision-engine:8000`

## Data Persistence

The following volumes persist data:
- `postgres_data` - Database data
- `redis_data` - Redis snapshots
- `kafka_data` - Kafka logs
- `zookeeper_data` - Zookeeper state
- `prometheus_data` - Metrics history
- `grafana_data` - Dashboards and config

## Troubleshooting

### Services not starting
```bash
# Check logs for specific service
docker-compose logs model-serving
docker-compose logs decision-engine
docker-compose logs rules-service

# Check all logs
make logs
```

### Health checks failing
```bash
# Wait longer - some services need 30-60s to start
make health

# Check individual service
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8003/health
```

### Port conflicts
If ports are already in use, you can modify them in `.env` or `docker-compose.yml`.

### Clean start
```bash
make down
make clean  # WARNING: This deletes all data
make build
make up
```

## Development Workflow

### Making changes to services

1. Make code changes in `services/{service-name}/`
2. Rebuild and restart:
   ```bash
   make rebuild
   ```

### Viewing logs

```bash
# All services
make logs

# Specific service
docker-compose logs -f decision-engine
```

### Database access

```bash
# PostgreSQL shell
make shell-postgres

# Then run SQL
SELECT * FROM decisions LIMIT 10;
```

### Redis access

```bash
# Redis CLI
make shell-redis

# Check keys
KEYS *
```

### Kafka topics

```bash
# List topics
make kafka-topics

# Consume messages
docker exec -it fraudguard-kafka kafka-console-consumer   --bootstrap-server localhost:9092   --topic decision_events   --from-beginning
```

## Production Considerations

This docker-compose setup is for **development only**. For production:

1. Use Kubernetes or similar orchestration
2. Externalize databases (managed PostgreSQL, Redis)
3. Use managed Kafka (Confluent Cloud, MSK)
4. Implement proper secrets management
5. Configure resource limits
6. Set up proper monitoring and alerting
7. Use production-grade ML model storage
8. Implement proper backup strategies

## Next Steps

1. Review the API documentation in each service's README
2. Set up Grafana dashboards (import from `platform/observability/grafana/`)
3. Configure alerting rules in Prometheus
4. Add custom rules via Rules Service API
5. Train and deploy updated ML models

## Support

For issues or questions, check:
- Service-specific READMEs in `services/{service-name}/`
- API documentation at `http://localhost:{port}/docs`
- Logs via `make logs`
