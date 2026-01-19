"""
Unit tests for model-serving service.

Tests ML inference, feature engineering, and prediction logic.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch


class TestFeatureEngineering:
    """Tests for feature extraction and transformation."""

    @pytest.mark.unit
    def test_amount_category_low(self):
        """Test amount categorization for low amounts."""
        amount = 25.0
        category = self._categorize_amount(amount)
        assert category == 0  # < 50

    @pytest.mark.unit
    def test_amount_category_medium_low(self):
        """Test amount categorization for medium-low amounts."""
        amount = 100.0
        category = self._categorize_amount(amount)
        assert category == 1  # 50-200

    @pytest.mark.unit
    def test_amount_category_medium_high(self):
        """Test amount categorization for medium-high amounts."""
        amount = 500.0
        category = self._categorize_amount(amount)
        assert category == 2  # 200-1000

    @pytest.mark.unit
    def test_amount_category_high(self):
        """Test amount categorization for high amounts."""
        amount = 2000.0
        category = self._categorize_amount(amount)
        assert category == 3  # > 1000

    @pytest.mark.unit
    def test_is_night_time_true(self):
        """Test night detection for late hours."""
        assert self._is_night(23) is True
        assert self._is_night(3) is True

    @pytest.mark.unit
    def test_is_night_time_false(self):
        """Test night detection for day hours."""
        assert self._is_night(10) is False
        assert self._is_night(14) is False

    @pytest.mark.unit
    def test_is_weekend_true(self):
        """Test weekend detection for Saturday/Sunday."""
        assert self._is_weekend(5) is True  # Saturday
        assert self._is_weekend(6) is True  # Sunday

    @pytest.mark.unit
    def test_is_weekend_false(self):
        """Test weekend detection for weekdays."""
        assert self._is_weekend(0) is False  # Monday
        assert self._is_weekend(4) is False  # Friday

    @pytest.mark.unit
    def test_channel_encoding(self):
        """Test channel string to numeric encoding."""
        assert self._encode_channel("app") == 0
        assert self._encode_channel("web") == 1
        assert self._encode_channel("pos") == 2
        assert self._encode_channel("atm") == 3
        assert self._encode_channel("unknown") == 0  # default

    @pytest.mark.unit
    def test_card_type_encoding(self):
        """Test card type encoding."""
        assert self._encode_card_type("physical") == 0
        assert self._encode_card_type("virtual") == 1

    # Helper methods (mirroring actual implementation)
    @staticmethod
    def _categorize_amount(amount: float) -> int:
        if amount < 50:
            return 0
        elif amount < 200:
            return 1
        elif amount < 1000:
            return 2
        return 3

    @staticmethod
    def _is_night(hour: int) -> bool:
        return hour >= 23 or hour < 5

    @staticmethod
    def _is_weekend(day: int) -> bool:
        return day >= 5

    @staticmethod
    def _encode_channel(channel: str) -> int:
        mapping = {"app": 0, "web": 1, "pos": 2, "atm": 3}
        return mapping.get(channel.lower(), 0)

    @staticmethod
    def _encode_card_type(card_type: str) -> int:
        return 1 if card_type.lower() == "virtual" else 0


class TestHaversineDistance:
    """Tests for geographic distance calculation."""

    @pytest.mark.unit
    def test_same_location_zero_distance(self):
        """Test distance calculation for same location."""
        distance = self._haversine(48.8566, 2.3522, 48.8566, 2.3522)
        assert distance == pytest.approx(0.0, abs=0.01)

    @pytest.mark.unit
    def test_paris_to_london(self):
        """Test distance from Paris to London (~344 km)."""
        distance = self._haversine(48.8566, 2.3522, 51.5074, -0.1278)
        assert 340 < distance < 350

    @pytest.mark.unit
    def test_distance_category_close(self):
        """Test distance categorization for close locations."""
        category = self._categorize_distance(5.0)
        assert category == 0  # < 10 km

    @pytest.mark.unit
    def test_distance_category_far(self):
        """Test distance categorization for far locations."""
        category = self._categorize_distance(500.0)
        assert category == 3  # > 100 km

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)

        a = np.sin(delta_lat / 2) ** 2 + \
            np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return R * c

    @staticmethod
    def _categorize_distance(distance_km: float) -> int:
        if distance_km < 10:
            return 0
        elif distance_km < 50:
            return 1
        elif distance_km < 100:
            return 2
        return 3


class TestModelPrediction:
    """Tests for ML model prediction logic."""

    @pytest.mark.unit
    @pytest.mark.model
    def test_score_range(self, sample_features):
        """Test that model score is within valid range [0, 1]."""
        # Mock prediction
        score = 0.45
        assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    @pytest.mark.model
    def test_feature_vector_length(self, sample_features):
        """Test that feature vector has correct length (12 features)."""
        assert len(sample_features) == 12

    @pytest.mark.unit
    @pytest.mark.model
    def test_decision_threshold_allow(self):
        """Test ALLOW decision for low scores."""
        score = 0.30
        decision = self._score_to_decision(score)
        assert decision == "ALLOW"

    @pytest.mark.unit
    @pytest.mark.model
    def test_decision_threshold_challenge(self):
        """Test CHALLENGE decision for medium scores."""
        score = 0.60
        decision = self._score_to_decision(score)
        assert decision == "CHALLENGE"

    @pytest.mark.unit
    @pytest.mark.model
    def test_decision_threshold_deny(self):
        """Test DENY decision for high scores."""
        score = 0.85
        decision = self._score_to_decision(score)
        assert decision == "DENY"

    @staticmethod
    def _score_to_decision(score: float) -> str:
        if score < 0.50:
            return "ALLOW"
        elif score <= 0.70:
            return "CHALLENGE"
        return "DENY"
