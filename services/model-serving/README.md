# FraudGuard AI - Model Serving Service

Real-time fraud detection model inference service built with FastAPI and LightGBM.

## Overview

The Model Serving service provides low-latency fraud prediction inference using a trained LightGBM model. It exposes REST API endpoints for predictions, health checks, and Prometheus metrics.

## Features

- **Fast Inference**: <30ms P95 latency for fraud predictions
- **RESTful API**: FastAPI-based HTTP endpoints
- **Health Monitoring**: Readiness and liveness checks
- **Prometheus Metrics**: Built-in observability
- **Docker Support**: Containerized deployment
- **Input Validation**: Pydantic models for type safety

## API Endpoints

### POST /predict

Make a fraud prediction for a transaction.

### GET /health

Health check endpoint.

### GET /metrics

Prometheus metrics endpoint.

## Installation

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

1. Build the image:
```bash
docker build -t fraudguard-model-serving:latest .
```

2. Run the container:
```bash
docker run -d -p 8000:8000 -v /path/to/models:/models fraudguard-model-serving:latest
```

## Configuration

Environment variables with prefix MODEL_SERVING_:
- MODEL_SERVING_MODEL_PATH: Path to LightGBM model file (default: /models/gbdt_v1.bin)
- MODEL_SERVING_PORT: Service port (default: 8000)

## Performance

- Latency Target: <30ms P95
- Optimized for LightGBM models

## License

Copyright 2025 FraudGuard AI
