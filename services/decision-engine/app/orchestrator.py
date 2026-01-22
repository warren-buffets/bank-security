"""
Orchestration logic for parallel service calls.
"""
import asyncio
import httpx
import logging
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from app.config import settings
from app.models import ScoreRequest, ScoreResponse, DecisionType

logger = logging.getLogger(__name__)


class DecisionOrchestrator:
    """Orchestrates parallel calls to Model Serving and Rules Service."""
    
    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize HTTP client."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.TOTAL_TIMEOUT_MS / 1000.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        logger.info("Orchestrator HTTP client initialized")
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            logger.info("Orchestrator HTTP client closed")
    
    async def call_model_serving(self, request: ScoreRequest) -> Tuple[Optional[float], List[str]]:
        """
        Call Model Serving service for ML score.
        
        Args:
            request: Score request
            
        Returns:
            Tuple of (score, feature_names)
        """
        if not self.http_client:
            logger.error("HTTP client not initialized")
            return None, []
        
        try:
            payload = {
                "event_id": request.event_id,
                "amount": request.amount,
                "currency": request.currency,
                "merchant": request.merchant.dict(exclude_none=True),
                "card": request.card.dict(exclude_none=True),
                "context": request.context.dict(exclude_none=True)
            }
            
            response = await self.http_client.post(
                f"{settings.MODEL_SERVING_URL}/predict",
                json=payload,
                timeout=settings.MODEL_SERVING_TIMEOUT_MS / 1000.0
            )
            response.raise_for_status()
            
            data = response.json()
            score = data.get("score")
            features = data.get("top_features", [])
            
            logger.debug(f"Model serving response: score={score}")
            return score, features
            
        except httpx.TimeoutException:
            logger.error(f"Model serving timeout after {settings.MODEL_SERVING_TIMEOUT_MS}ms")
            return None, []
        except Exception as e:
            logger.error(f"Error calling model serving: {e}")
            return None, []
    
    async def call_rules_service(self, request: ScoreRequest) -> Tuple[List[str], bool]:
        """
        Call Rules Service for rule evaluation.
        
        Args:
            request: Score request
            
        Returns:
            Tuple of (rule_hits, is_critical)
        """
        if not self.http_client:
            logger.error("HTTP client not initialized")
            return [], False
        
        try:
            payload = {
                "event_id": request.event_id,
                "tenant_id": request.tenant_id,
                "amount": request.amount,
                "currency": request.currency,
                "merchant": request.merchant.dict(exclude_none=True),
                "card": request.card.dict(exclude_none=True),
                "context": request.context.dict(exclude_none=True)
            }
            
            response = await self.http_client.post(
                f"{settings.RULES_SERVICE_URL}/evaluate",
                json=payload,
                timeout=settings.RULES_SERVICE_TIMEOUT_MS / 1000.0
            )
            response.raise_for_status()
            
            data = response.json()
            rule_hits = data.get("rule_hits", [])
            is_critical = data.get("critical", False)
            
            logger.debug(f"Rules service response: hits={len(rule_hits)}, critical={is_critical}")
            return rule_hits, is_critical
            
        except httpx.TimeoutException:
            logger.error(f"Rules service timeout after {settings.RULES_SERVICE_TIMEOUT_MS}ms")
            return [], False
        except Exception as e:
            logger.error(f"Error calling rules service: {e}")
            return [], False
    
    async def orchestrate(self, request: ScoreRequest) -> Dict[str, Any]:
        """
        Orchestrate parallel service calls and make decision.
        
        Args:
            request: Score request
            
        Returns:
            Decision result dictionary
        """
        start_time = datetime.utcnow()
        
        # Parallel calls to Model Serving and Rules Service
        model_task = self.call_model_serving(request)
        rules_task = self.call_rules_service(request)
        
        (score, top_features), (rule_hits, is_critical) = await asyncio.gather(
            model_task,
            rules_task,
            return_exceptions=False
        )
        
        # Make decision based on score, rules, and 2FA
        decision, reasons, requires_2fa = self._make_decision(
            score=score,
            rule_hits=rule_hits,
            is_critical=is_critical,
            has_initial_2fa=request.has_initial_2fa,
            top_features=top_features
        )
        
        # Calculate latency
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "decision": decision,
            "score": score,
            "rule_hits": rule_hits,
            "reasons": reasons,
            "requires_2fa": requires_2fa,
            "latency_ms": latency_ms,
            "model_version": settings.MODEL_VERSION
        }
    
    def _make_decision(
        self,
        score: Optional[float],
        rule_hits: List[str],
        is_critical: bool,
        has_initial_2fa: bool,
        top_features: List[str]
    ) -> Tuple[DecisionType, List[str], bool]:
        """
        Make final decision based on score, rules, and 2FA.
        
        Decision logic:
        1. If critical rule triggered -> DENY
        2. If score is None (ML failed) -> CHALLENGE (fail safe)
        3. If score > 0.70 -> CHALLENGE or DENY
        4. If score 0.50-0.70 and no 2FA -> CHALLENGE (request 2FA)
        5. If score 0.50-0.70 and has 2FA -> ALLOW (2FA sufficient)
        6. If score < 0.50 -> ALLOW
        
        Args:
            score: ML score [0..1]
            rule_hits: List of triggered rules
            is_critical: Whether critical rule was triggered
            has_initial_2fa: Whether 2FA was already performed
            top_features: Top contributing features
            
        Returns:
            Tuple of (decision, reasons, requires_2fa)
        """
        reasons = []
        requires_2fa = False
        
        # Critical rules override everything
        if is_critical:
            reasons.append("Critical security rule triggered")
            if rule_hits:
                reasons.append(f"Rules: {', '.join(rule_hits[:3])}")
            return DecisionType.DENY, reasons, False
        
        # ML failed - fail safe
        if score is None:
            reasons.append("Unable to compute risk score")
            return DecisionType.CHALLENGE, reasons, True
        
        # High risk score
        if score > settings.THRESHOLD_HIGH_RISK:
            reasons.append(f"High risk score: {score:.2f}")
            if top_features:
                reasons.append(f"Risk factors: {', '.join(top_features[:3])}")
            if rule_hits:
                reasons.append(f"Rules triggered: {', '.join(rule_hits[:3])}")
            return DecisionType.CHALLENGE, reasons, True
        
        # Medium risk score
        if score >= settings.THRESHOLD_LOW_RISK:
            reasons.append(f"Medium risk score: {score:.2f}")
            
            # If 2FA already done, allow
            if has_initial_2fa:
                reasons.append("2FA already validated")
                return DecisionType.ALLOW, reasons, False
            
            # Otherwise request 2FA
            reasons.append("2FA required for verification")
            requires_2fa = True
            return DecisionType.CHALLENGE, reasons, requires_2fa
        
        # Low risk - allow
        reasons.append(f"Low risk score: {score:.2f}")
        if rule_hits:
            reasons.append(f"Minor rules triggered: {', '.join(rule_hits[:2])}")
        else:
            reasons.append("No security rules triggered")
        
        return DecisionType.ALLOW, reasons, False


# Global instance
orchestrator = DecisionOrchestrator()
