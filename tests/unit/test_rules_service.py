"""
Unit tests for rules-service components.

Focus: rule DSL evaluation, rules engine matching, and allow/deny list checks.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest


ROOT = Path(__file__).resolve().parents[2]
RULES_SERVICE_PATH = ROOT / "services" / "rules-service"
sys.path.insert(0, str(RULES_SERVICE_PATH))

from app.rules_engine import RuleDSLEvaluator, RulesEngine  # noqa: E402
from app.lists_checker import ListsChecker  # noqa: E402


class TestRuleDslEvaluator:
    # Scenarios covered: simple comparison, AND/OR, IN list, NOT, velocity function, validation errors.

    @pytest.mark.unit
    def test_simple_comparison_true(self):
        evaluator = RuleDSLEvaluator()
        context = {"amount": 1500}
        assert evaluator.evaluate("amount > 1000", context) is True

    @pytest.mark.unit
    def test_and_expression_true(self):
        evaluator = RuleDSLEvaluator()
        context = {"amount": 1500, "geo": "RU", "user_home_geo": "US"}
        assert evaluator.evaluate("amount > 1000 AND geo != user_home_geo", context) is True

    @pytest.mark.unit
    def test_in_operator(self):
        evaluator = RuleDSLEvaluator()
        context = {"merchant_category": "gambling"}
        assert evaluator.evaluate("merchant_category IN ['gambling', 'crypto']", context) is True

    @pytest.mark.unit
    def test_not_operator(self):
        evaluator = RuleDSLEvaluator()
        context = {"is_international": False}
        assert evaluator.evaluate("NOT is_international", context) is True

    @pytest.mark.unit
    def test_velocity_function_amount(self):
        evaluator = RuleDSLEvaluator()
        context = {"amount_sum_24h": 8000}
        assert evaluator.evaluate("velocity_24h('amount') > 5000", context) is True

    @pytest.mark.unit
    def test_validate_empty_expression(self):
        evaluator = RuleDSLEvaluator()
        is_valid, error = evaluator.validate_expression("")
        assert is_valid is False
        assert error is not None

    @pytest.mark.unit
    def test_validate_unbalanced_quotes(self):
        evaluator = RuleDSLEvaluator()
        is_valid, error = evaluator.validate_expression("merchant_category IN ['gambling]")
        assert is_valid is False
        assert "Unbalanced" in error

    @pytest.mark.unit
    def test_validate_consecutive_logical_ops(self):
        evaluator = RuleDSLEvaluator()
        is_valid, error = evaluator.validate_expression("amount > 1000 AND OR geo == 'US'")
        assert is_valid is False
        assert "Consecutive" in error


class TestRulesEngine:
    # Scenarios covered: priority ordering, disabled rules skipped, basic match mapping.

    @pytest.mark.unit
    def test_matches_sorted_by_priority(self):
        engine = RulesEngine()
        rules = [
            {"id": "r1", "name": "low", "expression": "amount > 1000", "action": "review", "priority": 1},
            {"id": "r2", "name": "high", "expression": "amount > 1000", "action": "deny", "priority": 10},
        ]
        context = {"amount": 1500}
        matched = engine.evaluate_rules(rules, context)
        assert matched[0]["rule_id"] == "r2"
        assert matched[1]["rule_id"] == "r1"

    @pytest.mark.unit
    def test_disabled_rules_skipped(self):
        engine = RulesEngine()
        rules = [
            {"id": "r1", "name": "disabled", "expression": "amount > 1000", "action": "deny", "enabled": False},
            {"id": "r2", "name": "enabled", "expression": "amount > 1000", "action": "review", "enabled": True},
        ]
        context = {"amount": 1500}
        matched = engine.evaluate_rules(rules, context)
        assert len(matched) == 1
        assert matched[0]["rule_id"] == "r2"

    @pytest.mark.unit
    def test_match_payload_fields(self):
        engine = RulesEngine()
        rules = [
            {
                "id": "r1",
                "name": "high_amount",
                "expression": "amount > 1000",
                "action": "deny",
                "priority": 5,
                "metadata": {"severity": "high"},
                "description": "High amount"
            }
        ]
        context = {"amount": 1500}
        matched = engine.evaluate_rules(rules, context)
        assert matched[0]["rule_name"] == "high_amount"
        assert matched[0]["action"] == "deny"
        assert matched[0]["metadata"]["severity"] == "high"


class TestListsChecker:
    # Scenarios covered: deny match, allow match, add/remove list entry, decode list members.

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_deny_lists_match(self):
        redis_client = AsyncMock()
        redis_client.sismember.side_effect = [True]
        checker = ListsChecker(redis_client)
        context = {"user_id": "user_123"}
        matches = await checker.check_deny_lists(context)
        assert len(matches) == 1
        assert matches[0]["list_type"] == "deny"
        assert matches[0]["matched_value"] == "user_123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_allow_lists_match(self):
        redis_client = AsyncMock()
        redis_client.sismember.side_effect = [True]
        checker = ListsChecker(redis_client)
        context = {"user_id": "user_123"}
        matches = await checker.check_allow_lists(context)
        assert len(matches) == 1
        assert matches[0]["list_type"] == "allow"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_to_deny_list_with_ttl(self):
        redis_client = AsyncMock()
        checker = ListsChecker(redis_client)
        result = await checker.add_to_deny_list("user_id", "user_123", ttl=3600)
        assert result is True
        redis_client.sadd.assert_awaited_once()
        redis_client.expire.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_from_allow_list(self):
        redis_client = AsyncMock()
        checker = ListsChecker(redis_client)
        result = await checker.remove_from_allow_list("user_id", "user_123")
        assert result is True
        redis_client.srem.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_list_members_decodes_bytes(self):
        redis_client = AsyncMock()
        redis_client.smembers.return_value = {b"user_1", "user_2"}
        checker = ListsChecker(redis_client)
        members = await checker.get_list_members("deny", "user_id")
        assert members == {"user_1", "user_2"}
