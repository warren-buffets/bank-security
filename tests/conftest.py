"""
FraudGuard AI - Shared Test Fixtures

This module provides reusable fixtures for testing the fraud detection system.
"""

import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx

# Add services to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))


# =============================================================================
# Environment Configuration
# =============================================================================

@pytest.fixture(scope="session")
def test_config() -> dict:
    """Test configuration values."""
    return {
        "postgres_host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
        "postgres_port": int(os.getenv("TEST_POSTGRES_PORT", "5432")),
        "postgres_db": os.getenv("TEST_POSTGRES_DB", "antifraud_test"),
        "postgres_user": os.getenv("TEST_POSTGRES_USER", "postgres"),
        "postgres_password": os.getenv("TEST_POSTGRES_PASSWORD", "postgres_dev"),
        "redis_host": os.getenv("TEST_REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("TEST_REDIS_PORT", "6379")),
        "kafka_bootstrap_servers": os.getenv("TEST_KAFKA_SERVERS", "localhost:9092"),
        "model_serving_url": os.getenv("TEST_MODEL_URL", "http://localhost:8001"),
        "rules_service_url": os.getenv("TEST_RULES_URL", "http://localhost:8003"),
        "decision_engine_url": os.getenv("TEST_DECISION_URL", "http://localhost:8000"),
    }


# =============================================================================
# Sample Transaction Data
# =============================================================================

@pytest.fixture
def sample_transaction() -> dict:
    """Sample valid transaction for testing."""
    return {
        "event_id": "evt_test_001",
        "idempotency_key": "idem_test_001",
        "timestamp": "2024-01-15T10:30:00Z",
        "amount": 150.00,
        "currency": "EUR",
        "card_id": "card_123456",
        "merchant_id": "merch_789",
        "merchant_mcc": "5411",
        "merchant_name": "Test Grocery Store",
        "merchant_city": "Paris",
        "merchant_country": "FR",
        "channel": "pos",
        "card_type": "physical",
        "ip_address": "192.168.1.100",
        "device_id": "device_abc123",
        "user_lat": 48.8566,
        "user_lon": 2.3522,
        "merchant_lat": 48.8600,
        "merchant_lon": 2.3500,
    }


@pytest.fixture
def high_risk_transaction() -> dict:
    """High-risk transaction that should be flagged."""
    return {
        "event_id": "evt_test_risky",
        "idempotency_key": "idem_test_risky",
        "timestamp": "2024-01-15T03:30:00Z",  # Night time
        "amount": 5000.00,  # High amount
        "currency": "EUR",
        "card_id": "card_999999",
        "merchant_id": "merch_suspicious",
        "merchant_mcc": "6051",  # Crypto exchange
        "merchant_name": "Offshore Crypto",
        "merchant_city": "Unknown",
        "merchant_country": "XX",
        "channel": "web",
        "card_type": "virtual",
        "ip_address": "185.220.101.1",  # Tor exit node pattern
        "device_id": "device_new",
        "user_lat": 48.8566,
        "user_lon": 2.3522,
        "merchant_lat": -33.8688,  # Sydney - far away
        "merchant_lon": 151.2093,
    }


@pytest.fixture
def low_risk_transaction() -> dict:
    """Low-risk transaction that should be allowed."""
    return {
        "event_id": "evt_test_safe",
        "idempotency_key": "idem_test_safe",
        "timestamp": "2024-01-15T14:00:00Z",  # Afternoon
        "amount": 25.00,  # Low amount
        "currency": "EUR",
        "card_id": "card_trusted",
        "merchant_id": "merch_regular",
        "merchant_mcc": "5411",  # Grocery
        "merchant_name": "Local Supermarket",
        "merchant_city": "Paris",
        "merchant_country": "FR",
        "channel": "pos",
        "card_type": "physical",
        "ip_address": "192.168.1.1",
        "device_id": "device_known",
        "user_lat": 48.8566,
        "user_lon": 2.3522,
        "merchant_lat": 48.8570,
        "merchant_lon": 2.3525,
    }


# =============================================================================
# Mock Services
# =============================================================================

@pytest.fixture
def mock_model_response() -> dict:
    """Mock response from model-serving."""
    return {
        "score": 0.35,
        "model_version": "lgbm_kaggle_v1",
        "latency_ms": 15.5,
        "features_used": [
            "amt", "trans_hour", "trans_day", "merchant_mcc",
            "card_type", "channel", "is_international", "is_night",
            "is_weekend", "amount_category", "distance_category", "city_pop"
        ]
    }


@pytest.fixture
def mock_rules_response() -> dict:
    """Mock response from rules-service."""
    return {
        "matched_rules": [],
        "deny_list_match": False,
        "allow_list_match": False,
        "critical_rule_matched": False,
        "evaluation_time_ms": 12.3
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Mock httpx AsyncClient for service calls."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


# =============================================================================
# Database Fixtures (for integration tests)
# =============================================================================

@pytest.fixture
async def mock_db_pool() -> AsyncMock:
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    pool.release = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
async def mock_redis_client() -> AsyncMock:
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.close = AsyncMock()
    return redis


# =============================================================================
# HTTP Test Client Fixtures
# =============================================================================

@pytest.fixture
def anyio_backend() -> str:
    """Backend for anyio (used by httpx)."""
    return "asyncio"


# =============================================================================
# Feature Engineering Fixtures
# =============================================================================

@pytest.fixture
def sample_features() -> list:
    """Sample feature vector for model prediction."""
    return [
        150.0,   # amt
        10,      # trans_hour
        0,       # trans_day (Monday)
        5411,    # merchant_mcc
        0,       # card_type (physical)
        2,       # channel (pos)
        0,       # is_international
        0,       # is_night
        0,       # is_weekend
        1,       # amount_category (50-200)
        0,       # distance_category (close)
        100000,  # city_pop
    ]


# =============================================================================
# Utility Functions
# =============================================================================

def assert_decision_response(response: dict, expected_decision: str = None):
    """Assert that a decision response has the correct structure."""
    assert "decision" in response
    assert "score" in response
    assert "event_id" in response
    assert response["decision"] in ["ALLOW", "CHALLENGE", "DENY"]
    if expected_decision:
        assert response["decision"] == expected_decision


def assert_score_in_range(score: float, min_val: float = 0.0, max_val: float = 1.0):
    """Assert that a fraud score is within valid range."""
    assert min_val <= score <= max_val, f"Score {score} not in range [{min_val}, {max_val}]"
