-- FraudGuard AI - Analytics Queries
-- Useful queries for fraud analysis and monitoring

-- =============================================================================
-- DECISION ANALYTICS
-- =============================================================================

-- Decision distribution by day
SELECT
    DATE(created_at) as date,
    decision,
    COUNT(*) as count,
    ROUND(AVG(score)::numeric, 4) as avg_score
FROM decisions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), decision
ORDER BY date DESC, decision;

-- Decision rate over time (hourly)
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total,
    SUM(CASE WHEN decision = 'ALLOW' THEN 1 ELSE 0 END) as allowed,
    SUM(CASE WHEN decision = 'CHALLENGE' THEN 1 ELSE 0 END) as challenged,
    SUM(CASE WHEN decision = 'DENY' THEN 1 ELSE 0 END) as denied,
    ROUND(SUM(CASE WHEN decision = 'DENY' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as deny_rate
FROM decisions
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- Score distribution histogram
SELECT
    WIDTH_BUCKET(score, 0, 1, 10) as bucket,
    ROUND((WIDTH_BUCKET(score, 0, 1, 10) - 1) * 0.1, 1) as score_min,
    ROUND(WIDTH_BUCKET(score, 0, 1, 10) * 0.1, 1) as score_max,
    COUNT(*) as count
FROM decisions
GROUP BY WIDTH_BUCKET(score, 0, 1, 10)
ORDER BY bucket;

-- =============================================================================
-- TRANSACTION ANALYTICS
-- =============================================================================

-- Transaction volume by amount bucket
SELECT
    CASE
        WHEN amount < 50 THEN '< 50'
        WHEN amount < 200 THEN '50-200'
        WHEN amount < 1000 THEN '200-1000'
        ELSE '> 1000'
    END as amount_bucket,
    COUNT(*) as count,
    ROUND(AVG(amount)::numeric, 2) as avg_amount,
    SUM(amount) as total_amount
FROM events
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY
    CASE
        WHEN amount < 50 THEN '< 50'
        WHEN amount < 200 THEN '50-200'
        WHEN amount < 1000 THEN '200-1000'
        ELSE '> 1000'
    END
ORDER BY MIN(amount);

-- Top merchants by transaction count
SELECT
    e.merchant_id,
    COUNT(*) as tx_count,
    ROUND(AVG(e.amount)::numeric, 2) as avg_amount,
    SUM(e.amount) as total_amount,
    ROUND(AVG(d.score)::numeric, 4) as avg_risk_score
FROM events e
JOIN decisions d ON e.event_id = d.event_id
WHERE e.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY e.merchant_id
ORDER BY tx_count DESC
LIMIT 20;

-- High-risk merchants (avg score > 0.5)
SELECT
    e.merchant_id,
    COUNT(*) as tx_count,
    ROUND(AVG(d.score)::numeric, 4) as avg_score,
    SUM(CASE WHEN d.decision = 'DENY' THEN 1 ELSE 0 END) as denied_count,
    ROUND(SUM(CASE WHEN d.decision = 'DENY' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as deny_rate
FROM events e
JOIN decisions d ON e.event_id = d.event_id
WHERE e.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY e.merchant_id
HAVING AVG(d.score) > 0.5 AND COUNT(*) >= 10
ORDER BY avg_score DESC;

-- =============================================================================
-- RULE ANALYTICS
-- =============================================================================

-- Rule match frequency
SELECT
    r.rule_name,
    r.severity,
    r.action,
    COUNT(DISTINCT d.decision_id) as matches
FROM rules r
LEFT JOIN decisions d ON d.matched_rules @> ARRAY[r.rule_id]::uuid[]
WHERE r.is_active = true
AND d.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY r.rule_id, r.rule_name, r.severity, r.action
ORDER BY matches DESC;

-- =============================================================================
-- LATENCY ANALYTICS
-- =============================================================================

-- Decision latency percentiles
SELECT
    DATE(created_at) as date,
    COUNT(*) as count,
    ROUND(AVG(latency_ms)::numeric, 2) as avg_latency,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) as p50,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) as p90,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) as p95,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) as p99,
    MAX(latency_ms) as max_latency
FROM decisions
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Slow decisions (> 100ms)
SELECT
    decision_id,
    event_id,
    decision,
    score,
    latency_ms,
    created_at
FROM decisions
WHERE latency_ms > 100
AND created_at >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY latency_ms DESC
LIMIT 50;

-- =============================================================================
-- FRAUD PATTERN DETECTION
-- =============================================================================

-- Cards with multiple high-risk transactions
SELECT
    e.card_id,
    COUNT(*) as tx_count,
    SUM(CASE WHEN d.score > 0.7 THEN 1 ELSE 0 END) as high_risk_count,
    ROUND(AVG(d.score)::numeric, 4) as avg_score,
    SUM(e.amount) as total_amount
FROM events e
JOIN decisions d ON e.event_id = d.event_id
WHERE e.created_at >= CURRENT_DATE - INTERVAL '24 hours'
GROUP BY e.card_id
HAVING SUM(CASE WHEN d.score > 0.7 THEN 1 ELSE 0 END) >= 2
ORDER BY high_risk_count DESC, avg_score DESC;

-- Velocity check: cards with > 3 transactions in 5 minutes
WITH velocity AS (
    SELECT
        card_id,
        created_at,
        COUNT(*) OVER (
            PARTITION BY card_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '5 minutes' PRECEDING AND CURRENT ROW
        ) as tx_in_5min
    FROM events
    WHERE created_at >= NOW() - INTERVAL '1 hour'
)
SELECT DISTINCT
    card_id,
    MAX(tx_in_5min) as max_velocity
FROM velocity
WHERE tx_in_5min > 3
GROUP BY card_id
ORDER BY max_velocity DESC;

-- International transactions pattern
SELECT
    e.card_id,
    COUNT(DISTINCT e.merchant_country) as countries,
    STRING_AGG(DISTINCT e.merchant_country, ', ') as country_list,
    COUNT(*) as tx_count,
    SUM(e.amount) as total_amount
FROM events e
WHERE e.created_at >= CURRENT_DATE - INTERVAL '24 hours'
GROUP BY e.card_id
HAVING COUNT(DISTINCT e.merchant_country) >= 3
ORDER BY countries DESC;

-- =============================================================================
-- REPORTING
-- =============================================================================

-- Daily summary report
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN decision = 'ALLOW' THEN 1 ELSE 0 END) as allowed,
    SUM(CASE WHEN decision = 'CHALLENGE' THEN 1 ELSE 0 END) as challenged,
    SUM(CASE WHEN decision = 'DENY' THEN 1 ELSE 0 END) as denied,
    ROUND(AVG(score)::numeric, 4) as avg_score,
    ROUND(AVG(latency_ms)::numeric, 2) as avg_latency_ms
FROM decisions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
