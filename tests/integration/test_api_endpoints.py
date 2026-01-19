"""
Integration tests for API endpoints.

These tests require Docker services to be running.
Run with: pytest tests/integration -m integration
"""

import pytest
import httpx
from typing import AsyncGenerator


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


class TestModelServingAPI:
    """Integration tests for model-serving service."""

    BASE_URL = "http://localhost:8001"

    @pytest.mark.integration
    @pytest.mark.api
    async def test_health_endpoint(self, http_client: httpx.AsyncClient):
        """Test model-serving health endpoint."""
        response = await http_client.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.model
    async def test_predict_endpoint(self, http_client: httpx.AsyncClient, sample_transaction):
        """Test model-serving prediction endpoint."""
        response = await http_client.post(
            f"{self.BASE_URL}/predict",
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert 0.0 <= data["score"] <= 1.0
        assert "latency_ms" in data

    @pytest.mark.integration
    @pytest.mark.api
    async def test_metrics_endpoint(self, http_client: httpx.AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await http_client.get(f"{self.BASE_URL}/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")


class TestRulesServiceAPI:
    """Integration tests for rules-service."""

    BASE_URL = "http://localhost:8003"

    @pytest.mark.integration
    @pytest.mark.api
    async def test_health_endpoint(self, http_client: httpx.AsyncClient):
        """Test rules-service health endpoint."""
        response = await http_client.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.api
    async def test_evaluate_endpoint(self, http_client: httpx.AsyncClient, sample_transaction):
        """Test rules evaluation endpoint."""
        response = await http_client.post(
            f"{self.BASE_URL}/evaluate",
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.json()
        assert "matched_rules" in data
        assert "deny_list_match" in data
        assert "allow_list_match" in data


class TestDecisionEngineAPI:
    """Integration tests for decision-engine service."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.integration
    @pytest.mark.api
    async def test_health_endpoint(self, http_client: httpx.AsyncClient):
        """Test decision-engine health endpoint."""
        response = await http_client.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.api
    async def test_score_endpoint(self, http_client: httpx.AsyncClient, sample_transaction):
        """Test main scoring endpoint."""
        response = await http_client.post(
            f"{self.BASE_URL}/v1/score",
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.json()
        assert "decision" in data
        assert data["decision"] in ["ALLOW", "CHALLENGE", "DENY"]
        assert "score" in data
        assert "event_id" in data

    @pytest.mark.integration
    @pytest.mark.api
    async def test_score_idempotency(self, http_client: httpx.AsyncClient, sample_transaction):
        """Test idempotency - same request returns same result."""
        # First request
        response1 = await http_client.post(
            f"{self.BASE_URL}/v1/score",
            json=sample_transaction
        )
        data1 = response1.json()

        # Second request with same idempotency_key
        response2 = await http_client.post(
            f"{self.BASE_URL}/v1/score",
            json=sample_transaction
        )
        data2 = response2.json()

        # Should return identical decisions
        assert data1["decision"] == data2["decision"]
        assert data1["score"] == data2["score"]

    @pytest.mark.integration
    @pytest.mark.api
    async def test_high_risk_transaction(self, http_client: httpx.AsyncClient, high_risk_transaction):
        """Test that high-risk transactions are flagged."""
        response = await http_client.post(
            f"{self.BASE_URL}/v1/score",
            json=high_risk_transaction
        )
        assert response.status_code == 200
        data = response.json()
        # High risk should result in CHALLENGE or DENY
        assert data["decision"] in ["CHALLENGE", "DENY"]
        assert data["score"] > 0.5

    @pytest.mark.integration
    @pytest.mark.api
    async def test_low_risk_transaction(self, http_client: httpx.AsyncClient, low_risk_transaction):
        """Test that low-risk transactions are allowed."""
        response = await http_client.post(
            f"{self.BASE_URL}/v1/score",
            json=low_risk_transaction
        )
        assert response.status_code == 200
        data = response.json()
        # Low risk should result in ALLOW
        assert data["decision"] == "ALLOW"
        assert data["score"] < 0.5


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.mark.integration
    @pytest.mark.database
    async def test_postgres_connection(self, test_config):
        """Test PostgreSQL connectivity."""
        import asyncpg

        try:
            conn = await asyncpg.connect(
                host=test_config["postgres_host"],
                port=test_config["postgres_port"],
                database=test_config["postgres_db"],
                user=test_config["postgres_user"],
                password=test_config["postgres_password"],
            )
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            assert result == 1
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    @pytest.mark.integration
    @pytest.mark.redis
    async def test_redis_connection(self, test_config):
        """Test Redis connectivity."""
        import redis.asyncio as redis

        try:
            client = redis.Redis(
                host=test_config["redis_host"],
                port=test_config["redis_port"],
            )
            result = await client.ping()
            await client.close()
            assert result is True
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
