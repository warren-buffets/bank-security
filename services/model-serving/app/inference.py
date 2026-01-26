"""ML inference engine for fraud detection."""
import time
import logging
import pickle
import os
from typing import List, Optional
import numpy as np
import lightgbm as lgb
from prometheus_client import Counter, Histogram, Gauge

from .config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTION_COUNTER = Counter(
    'model_predictions_total',
    'Total number of predictions made',
    ['model_version']
)

PREDICTION_LATENCY = Histogram(
    'model_prediction_latency_seconds',
    'Prediction latency in seconds',
    ['model_version'],
    buckets=[0.001, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.05, 0.1]
)

FRAUD_SCORE_DISTRIBUTION = Histogram(
    'fraud_score_distribution',
    'Distribution of fraud scores',
    ['model_version'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

MODEL_LOAD_TIME = Gauge(
    'model_load_time_seconds',
    'Time taken to load the model'
)


class ModelInference:
    """Handles model loading and inference."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize the inference engine.

        Args:
            model_path: Path to the LightGBM model file
        """
        self.model_path = model_path or settings.model_path
        self.model: Optional[lgb.Booster] = None
        self.calibrator = None  # Platt scaling calibrator
        self.model_version = "gbdt_v2_calibrated"
        self.feature_names = settings.expected_features

    def load_model(self) -> None:
        """Load the LightGBM model and calibrator from disk."""
        start_time = time.time()
        try:
            logger.info(f"Loading model from {self.model_path}")
            self.model = lgb.Booster(model_file=self.model_path)

            # Try to load calibrator if available
            calibrator_path = os.path.join(
                os.path.dirname(self.model_path),
                'score_calibrator.pkl'
            )
            if os.path.exists(calibrator_path):
                with open(calibrator_path, 'rb') as f:
                    self.calibrator = pickle.load(f)
                logger.info(f"Calibrator loaded from {calibrator_path}")
            else:
                logger.warning(f"No calibrator found at {calibrator_path}, using raw scores")

            load_time = time.time() - start_time
            MODEL_LOAD_TIME.set(load_time)
            logger.info(f"Model loaded successfully in {load_time:.3f}s")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None
    
    def predict(self, features: List[float]) -> float:
        """Make a fraud prediction.
        
        Args:
            features: List of feature values in expected order
            
        Returns:
            Fraud probability score between 0 and 1
            
        Raises:
            RuntimeError: If model is not loaded
            ValueError: If features are invalid
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        if len(features) != len(self.feature_names):
            raise ValueError(
                f"Expected {len(self.feature_names)} features, got {len(features)}"
            )
        
        # Record prediction latency
        start_time = time.time()
        
        try:
            # Convert to numpy array and reshape for prediction
            features_array = np.array(features).reshape(1, -1)

            # Make prediction (raw score)
            raw_score = self.model.predict(features_array)[0]

            # Apply calibration if available (linear stretch)
            if self.calibrator is not None:
                scale = self.calibrator.get('scale', 1.0)
                offset = self.calibrator.get('offset', 0.0)
                calibrated = scale * raw_score + offset
                fraud_score = float(np.clip(calibrated, 0.0, 1.0))
                logger.debug(f"Raw score: {raw_score:.4f} -> Calibrated: {fraud_score:.4f}")
            else:
                fraud_score = float(np.clip(raw_score, 0.0, 1.0))
            
            # Record metrics
            latency = time.time() - start_time
            PREDICTION_LATENCY.labels(model_version=self.model_version).observe(latency)
            PREDICTION_COUNTER.labels(model_version=self.model_version).inc()
            FRAUD_SCORE_DISTRIBUTION.labels(model_version=self.model_version).observe(fraud_score)
            
            latency_ms = latency * 1000
            logger.debug(f"Prediction completed in {latency_ms:.2f}ms, score: {fraud_score:.4f}")
            
            return fraud_score
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {e}")
    
    def get_feature_importance(self) -> dict:
        """Get feature importance from the model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        importance = self.model.feature_importance()
        return dict(zip(self.feature_names, importance.tolist()))


# Global model instance
model_inference = ModelInference()
