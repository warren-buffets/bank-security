"""FastAPI application for fraud detection model serving."""
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

from .config import settings
from .models import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse
)
from .inference import model_inference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNTER = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting FraudGuard Model Serving service")
    logger.info(f"Model path: {settings.model_path}")

    try:
        model_inference.load_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")

    yield

    logger.info("Shutting down FraudGuard Model Serving service")


app = FastAPI(
    title="FraudGuard AI - Model Serving",
    description="Real-time fraud detection model inference API",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    """Middleware to track request metrics."""
    start_time = time.time()
    response = await call_next(request)
    
    latency = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNTER.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

    return response


@app.get("/", tags=["Info"])
async def root() -> Dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "predict": "/predict",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    uptime = time.time() - SERVICE_START_TIME

    return HealthResponse(
        status="healthy" if model_inference.is_loaded() else "degraded",
        model_loaded=model_inference.is_loaded(),
        model_path=settings.model_path,
        uptime_seconds=uptime
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Make a fraud prediction for a transaction.

    Args:
        request: Prediction request with transaction data

    Returns:
        PredictionResponse with fraud score and metadata
    """
    if not model_inference.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is not ready."
        )

    start_time = time.time()

    try:
        # Get current time for temporal features
        dt = datetime.now()
        trans_hour = dt.hour
        trans_day = dt.weekday()  # 0=Monday, 6=Sunday
        
        # Extract merchant data
        merchant_mcc = int(request.merchant.get('mcc', 5999))
        merchant_country = request.merchant.get('country', 'FR')
        is_merchant_international = 1 if merchant_country != 'FR' else 0
        
        # Extract card data
        card_type_str = request.card.get('type', 'physical')
        card_type = 1 if card_type_str == 'virtual' else 0
        
        # Extract context
        channel_map = {'app': 0, 'web': 1, 'pos': 2, 'atm': 3}
        channel = channel_map.get(request.context.get('channel', 'app'), 0)
        
        context_geo = request.context.get('geo', 'FR')
        is_international = 1 if context_geo != 'FR' else 0
        
        # Calculate derived features
        is_night = 1 if (trans_hour >= 23 or trans_hour <= 5) else 0
        is_weekend = 1 if trans_day >= 5 else 0
        
        # Amount category: 0=<50, 1=50-200, 2=200-1000, 3=>1000
        amount = request.amount
        if amount < 50:
            amount_category = 0
        elif amount < 200:
            amount_category = 1
        elif amount < 1000:
            amount_category = 2
        else:
            amount_category = 3
        
        # Build feature vector in correct order (matching training)
        feature_values = [
            amount,                    # amount
            trans_hour,                # trans_hour
            trans_day,                 # trans_day
            merchant_mcc,              # merchant_mcc
            is_merchant_international, # merchant_country
            card_type,                 # card_type
            channel,                   # channel
            is_international,          # is_international
            is_night,                  # is_night
            is_weekend,                # is_weekend
            amount_category            # amount_category
        ]

        # Make prediction
        fraud_score = model_inference.predict(feature_values)

        # Calculate prediction time
        prediction_time_ms = (time.time() - start_time) * 1000

        # Log if exceeds SLA
        if prediction_time_ms > settings.max_prediction_time_ms:
            logger.warning(
                f"Prediction time {prediction_time_ms:.2f}ms exceeds "
                f"SLA of {settings.max_prediction_time_ms}ms"
            )

        # Top features based on importance
        top_features = ["merchant_mcc", "amount", "is_night"]

        return PredictionResponse(
            event_id=request.event_id,
            score=fraud_score,
            top_features=top_features,
            prediction_time_ms=round(prediction_time_ms, 2),
            model_version="fraud_lgbm_mvp_v1"
        )

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=None
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level="info"
    )
