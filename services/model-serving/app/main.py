"""FastAPI application for fraud detection model serving - Kaggle model."""
import time
import logging
import math
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
from .geolocation import geolocate_ip

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


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers using Haversine formula."""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_distance_category(distance_km: float) -> int:
    """Convert distance to category: 0 (<10km), 1 (10-50km), 2 (50-200km), 3 (>200km)."""
    if distance_km < 10:
        return 0
    elif distance_km < 50:
        return 1
    elif distance_km < 200:
        return 2
    else:
        return 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting FraudGuard Model Serving service - Kaggle model")
    logger.info(f"Model path: {settings.model_path}")

    try:
        model_inference.load_model()
        logger.info("✓ Kaggle model loaded successfully (12 features)")
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")

    yield

    logger.info("Shutting down FraudGuard Model Serving service")


app = FastAPI(
    title="FraudGuard AI - Model Serving",
    description="Real-time fraud detection model inference API (Kaggle model)",
    version="2.0.0",
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
        "version": "2.0.0",
        "model": "kaggle_lgbm_v1",
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

        # Extract amount
        amount = request.amount

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
        is_international = is_merchant_international  # Same as merchant for now

        # Derived features
        is_night = 1 if (trans_hour >= 23 or trans_hour <= 5) else 0
        is_weekend = 1 if trans_day >= 5 else 0

        # Amount category adjusted for European banking context
        # Thresholds: [100, 500, 2000] - more realistic for legitimate purchases
        # 0: <100€ (small daily purchases)
        # 1: 100-500€ (regular purchases)
        # 2: 500-2000€ (large purchases)
        # 3: >2000€ (exceptional purchases)
        if amount < 100:
            amount_category = 0
        elif amount < 500:
            amount_category = 1
        elif amount < 2000:
            amount_category = 2
        else:
            amount_category = 3

        # Geolocation from IP address
        user_ip = request.context.get('ip')
        user_lat = request.context.get('user_lat')
        user_long = request.context.get('user_long')
        city_pop = request.context.get('city_pop')

        # If IP provided but no coordinates, geolocate the IP
        if user_ip and not all([user_lat, user_long]):
            geo = await geolocate_ip(user_ip)
            if geo.success:
                user_lat = geo.lat
                user_long = geo.lon
                city_pop = geo.city_pop
                logger.info(f"Geolocated IP {user_ip} -> {geo.city} ({geo.lat}, {geo.lon}), pop={geo.city_pop}")
            else:
                logger.warning(f"IP geolocation failed for {user_ip}: {geo.error}")

        # Use defaults if still not available
        if city_pop is None:
            city_pop = settings.default_city_pop

        # Distance category (calculated from geo coordinates)
        merch_lat = request.merchant.get('lat')
        merch_long = request.merchant.get('long')

        if all([user_lat, user_long, merch_lat, merch_long]):
            # Calculate actual distance
            distance_km = haversine_distance(user_lat, user_long, merch_lat, merch_long)
            distance_category = calculate_distance_category(distance_km)
            logger.info(f"Calculated distance: {distance_km:.2f}km (category {distance_category})")
        else:
            # Use default if geo data not provided
            distance_category = settings.default_distance_category
            logger.debug(f"Using default distance category: {distance_category}")

        # Build feature vector in exact order expected by Kaggle model
        # Order: amt, trans_hour, trans_day, merchant_mcc, card_type, channel,
        #        is_international, is_night, is_weekend, amount_category,
        #        distance_category, city_pop
        feature_values = [
            amount,
            trans_hour,
            trans_day,
            merchant_mcc,
            card_type,
            channel,
            is_international,
            is_night,
            is_weekend,
            amount_category,
            distance_category,
            city_pop
        ]

        # Log features for debugging
        logger.info(f"Features: amt={amount}, hour={trans_hour}, day={trans_day}, "
                    f"mcc={merchant_mcc}, card_type={card_type}, channel={channel}, "
                    f"is_intl={is_international}, is_night={is_night}, is_weekend={is_weekend}, "
                    f"amt_cat={amount_category}, dist_cat={distance_category}, city_pop={city_pop}")

        # Make prediction
        fraud_score = model_inference.predict(feature_values)

        # Calculate latency
        prediction_time_ms = round((time.time() - start_time) * 1000, 2)

        # Top features (from Kaggle model training)
        top_features = ["amount_category", "trans_hour", "amt"]

        return PredictionResponse(
            event_id=request.event_id,
            score=fraud_score,
            top_features=top_features,
            prediction_time_ms=prediction_time_ms,
            model_version="fraud_lgbm_kaggle_v1"
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
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
