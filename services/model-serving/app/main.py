"""FastAPI application for fraud detection model serving."""
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
from fastapi.responses import Response

from .config import settings
from .models import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse,
    TransactionFeatures
)
from .inference import model_inference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Additional metrics
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

# Track service start time
SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FraudGuard Model Serving service")
    logger.info(f"Model path: {settings.model_path}")
    
    try:
        model_inference.load_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")
        # Continue running to allow health checks to report the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down FraudGuard Model Serving service")


# Create FastAPI app
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
    
    # Record metrics
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
    """Health check endpoint.
    
    Returns:
        HealthResponse with service status and model information
    """
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
        request: Prediction request with transaction features
        
    Returns:
        PredictionResponse with fraud score and metadata
        
    Raises:
        HTTPException: If model is not loaded or prediction fails
    """
    if not model_inference.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is not ready."
        )
    
    start_time = time.time()
    
    try:
        # Extract features in the correct order
        features = request.features
        feature_values = [
            features.amount,
            features.hour,
            features.day_of_week,
            features.merchant_risk_score,
            features.card_present,
            features.international,
            features.high_risk_country,
            features.velocity_1h,
            features.velocity_24h,
            features.avg_amount_30d
        ]
        
        # Make prediction
        fraud_score = model_inference.predict(feature_values)
        
        # Calculate prediction time
        prediction_time_ms = (time.time() - start_time) * 1000
        
        # Check if prediction meets SLA
        if prediction_time_ms > settings.max_prediction_time_ms:
            logger.warning(
                f"Prediction time {prediction_time_ms:.2f}ms exceeds "
                f"SLA of {settings.max_prediction_time_ms}ms"
            )
        
        return PredictionResponse(
            transaction_id=request.transaction_id,
            fraud_score=fraud_score,
            prediction_time_ms=round(prediction_time_ms, 2),
            model_version=model_inference.model_version
        )
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
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
