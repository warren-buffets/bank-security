# Flux de Données - FraudGuard AI

## 🎯 Vue d'ensemble

Ce document détaille tous les flux de données du système FraudGuard AI, depuis la transaction client jusqu'au feedback ML.

---

## 🔄 Flux 1 : Scoring temps réel (synchrone)

### Transaction → Décision (< 100ms)

```
┌─────────────┐
│   CLIENT    │ POST /v1/score
│             │ {tenant_id, idempotency_key, event}
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│         DECISION ENGINE                      │
│                                              │
│  ÉTAPE 1 : Idempotence                      │
│  ┌────────────────────────────────────────┐ │
│  │ Redis GET(idempotency_key)             │ │
│  │ Si existe → Retourner réponse cachée   │ │
│  │ Sinon → Continuer                      │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ÉTAPE 2 : Feature Engineering              │
│  ┌────────────────────────────────────────┐ │
│  │ Parse event payload                    │ │
│  │ Redis GET vélocités (tx_per_5m)       │ │
│  │ Redis GET device_risk_score           │ │
│  │ Calcul features dérivées              │ │
│  │ → Feature vector [50-100 dims]        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ÉTAPE 3 : Scoring Parallèle                │
│  ┌────────────────────────────────────────┐ │
│  │ Thread 1 → RULES SERVICE               │ │
│  │   • Évalue règles DSL                 │ │
│  │   • Check deny lists                  │ │
│  │   • Timeout 50ms                      │ │
│  │   • Return: rule_hits[]               │ │
│  │                                        │ │
│  │ Thread 2 → MODEL SERVING               │ │
│  │   • GBDT.predict_proba(features)      │ │
│  │   • Timeout 30ms                      │ │
│  │   • Return: score [0..1]              │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ÉTAPE 4 : Agrégation Décision              │
│  ┌────────────────────────────────────────┐ │
│  │ IF rule_hits contient DENY             │ │
│  │   → decision = DENY                    │ │
│  │ ELIF score > 0.70                      │ │
│  │   → decision = DENY ou CHALLENGE       │ │
│  │ ELIF score > 0.50                      │ │
│  │   IF 2FA déjà validé                   │ │
│  │     → decision = ALLOW                 │ │
│  │   ELSE                                 │ │
│  │     → decision = CHALLENGE (2FA)       │ │
│  │ ELSE                                   │ │
│  │   → decision = ALLOW                   │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ÉTAPE 5 : Persistance                      │
│  ┌────────────────────────────────────────┐ │
│  │ Postgres INSERT events                 │ │
│  │ Postgres INSERT decisions              │ │
│  │ Redis SET idempotency_key (TTL 24h)   │ │
│  │ Kafka PUBLISH decision_event           │ │
│  └────────────────────────────────────────┘ │
└──────────────┬───────────────────────────────┘
               │
               ▼
         ┌──────────┐
         │  CLIENT  │ {decision, score, latency_ms}
         └──────────┘

Latence totale : 45-100ms (P95)
```

---

## 🔄 Flux 2 : Case Management (asynchrone)

### Transaction suspecte → Investigation analyste

```
┌────────────────────┐
│ DECISION ENGINE    │ Decision = CHALLENGE ou DENY
└─────────┬──────────┘
          │
          ▼ Kafka topic: decision_events
┌─────────────────────────────────────────┐
│         KAFKA BROKER                    │
│  Topic: decision_events                 │
│  Partition: par tenant_id               │
│  Rétention: 7 jours                     │
└─────────┬───────────────────────────────┘
          │
          ▼ Consumer Group: case-service
┌─────────────────────────────────────────┐
│         CASE SERVICE                    │
│                                         │
│  1. Filter: CHALLENGE ou DENY           │
│                                         │
│  2. Calcul priorité:                    │
│     • score > 0.8 → priority = 2 (high) │
│     • score 0.5-0.8 → priority = 1 (med)│
│                                         │
│  3. Assignation queue:                  │
│     • DENY → queue = "high_risk"        │
│     • CHALLENGE + score > 0.7           │
│       → queue = "medium_risk"           │
│     • CHALLENGE + score < 0.7           │
│       → queue = "review"                │
│                                         │
│  4. CREATE case:                        │
│     ┌─────────────────────────────────┐│
│     │ case_id: UUID                   ││
│     │ event_id: référence transaction ││
│     │ queue: high_risk/medium/review  ││
│     │ priority: 0/1/2                 ││
│     │ status: open                    ││
│     │ assignee: null (ou auto-assign) ││
│     │ metadata: {amount, merchant...} ││
│     └─────────────────────────────────┘│
│                                         │
│  5. Postgres INSERT cases               │
│                                         │
│  6. Notification:                       │
│     • Slack webhook                     │
│     • Email analyste                    │
│     • Dashboard temps réel              │
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         CASE UI (Interface)             │
│                                         │
│  Analyste voit case dans sa queue       │
│                                         │
│  Investigation:                         │
│  • Détails transaction                  │
│  • Score ML + raisons                   │
│  • Profil utilisateur                   │
│  • Historique vélocité                  │
│                                         │
│  Décision analyste:                     │
│  ┌────────────────────────────────────┐│
│  │ APPROVE                            ││
│  │  → UPDATE cases (closed)           ││
│  │  → INSERT labels (legit)           ││
│  │  → Notify client (SMS approved)    ││
│  │                                    ││
│  │ REJECT                             ││
│  │  → UPDATE cases (fraud_confirmed)  ││
│  │  → INSERT labels (fraud)           ││
│  │  → Block card                      ││
│  │                                    ││
│  │ CONTACT                            ││
│  │  → UPDATE cases (waiting_response) ││
│  │  → Send SMS/Call                   ││
│  │  → Timeout 30min → auto-reject     ││
│  └────────────────────────────────────┘│
└─────────────────────────────────────────┘

Timeline:
• T+0s : Transaction CHALLENGE
• T+2s : Case créé
• T+5min : Analyste ouvre case
• T+7min : Décision analyste
• T+8min : Case fermé + Label ML
```

---

## 🔄 Flux 3 : Feature Store (temps réel)

### Mise à jour features online (vélocités, flags)

```
┌────────────────────┐
│ DECISION ENGINE    │ Transaction processed
└─────────┬──────────┘
          │
          ▼ Kafka: tx_events
┌─────────────────────────────────────────┐
│    FEATURE UPDATER (Background)         │
│    (Consumer Kafka)                     │
│                                         │
│  Pour chaque transaction:               │
│                                         │
│  1. Extraire identifiants:              │
│     • user_id                           │
│     • card_id                           │
│     • device_id                         │
│     • merchant_id                       │
│                                         │
│  2. Update vélocités (Redis):           │
│     ┌─────────────────────────────────┐│
│     │ ZADD velocity:{card_id}         ││
│     │   score={timestamp}             ││
│     │   member={tx_id}                ││
│     │                                 ││
│     │ ZREMRANGEBYSCORE (cleanup)      ││
│     │   Remove tx older than 1 hour   ││
│     │                                 ││
│     │ EXPIRE velocity:{card_id} 3600  ││
│     └─────────────────────────────────┘│
│                                         │
│  3. Update device flags:                │
│     ┌─────────────────────────────────┐│
│     │ SET device:{device_id}          ││
│     │   {                             ││
│     │     first_seen: timestamp,      ││
│     │     last_country: "FR",         ││
│     │     risk_score: 0.2             ││
│     │   }                             ││
│     │ EXPIRE 86400 (24h)              ││
│     └─────────────────────────────────┘│
│                                         │
│  4. Update user geo history:            │
│     ┌─────────────────────────────────┐│
│     │ SADD user:{user_id}:countries   ││
│     │   "FR" "DE" "ES"                ││
│     │ EXPIRE 604800 (7 days)          ││
│     └─────────────────────────────────┘│
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         REDIS (Feature Store)           │
│                                         │
│  Structures:                            │
│                                         │
│  velocity:{card_id}                     │
│    Sorted Set (score=timestamp)        │
│    → ZCOUNT last 5min = tx_per_5min    │
│    TTL: 1 hour                          │
│                                         │
│  device:{device_id}                     │
│    Hash {first_seen, last_country...}  │
│    TTL: 24 hours                        │
│                                         │
│  user:{user_id}:countries               │
│    Set ["FR", "DE", "ES"]               │
│    TTL: 7 days                          │
│                                         │
│  merchant:{merchant_id}:risk            │
│    String "0.45"                        │
│    TTL: 24 hours                        │
└─────────────────────────────────────────┘

Performance:
• UPDATE latency: 2-5ms par transaction
• GET latency: < 1ms (pendant scoring)
• Memory bounded: TTL auto-expiration
```

---

## 🔄 Flux 4 : ML Training Pipeline (offline)

### Labels → Retraining → Déploiement

```
┌─────────────────────────────────────────┐
│         DATA LAKE (S3/MinIO)            │
│                                         │
│  • events_YYYYMMDD.parquet              │
│  • decisions_YYYYMMDD.parquet           │
│  • labels_YYYYMMDD.parquet              │
│                                         │
│  Partitionnement: date + tenant_id      │
└─────────┬───────────────────────────────┘
          │
          ▼ ETL Spark/Dask (nightly)
┌─────────────────────────────────────────┐
│    FEATURE ENGINEERING OFFLINE          │
│                                         │
│  1. Load data (7-30 derniers jours)     │
│                                         │
│  2. Join events + decisions + labels    │
│                                         │
│  3. Compute features:                   │
│     • Vélocités historiques             │
│     • Patterns comportementaux          │
│     • Aggregations merchant/device      │
│                                         │
│  4. Train/Valid/Test split (temporal)   │
│     • Train: J-30 à J-8                 │
│     • Valid: J-7 à J-4                  │
│     • Test: J-3 à J-1                   │
│                                         │
│  5. Output: training.parquet            │
│     [features] + [label]                │
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         TRAINING JOB (Airflow)          │
│                                         │
│  1. Load training.parquet               │
│                                         │
│  2. Train GBDT (LightGBM):              │
│     • Hyperparams: Optuna tuning        │
│     • Objective: binary cross-entropy   │
│     • Early stopping on validation      │
│                                         │
│  3. Calibration:                        │
│     • Platt scaling ou Isotonic         │
│     • Sur validation set propre         │
│                                         │
│  4. Seuil optimization:                 │
│     • Coût FP vs FN (matrice coûts)     │
│     • Contrainte: FP_rate < 2%          │
│     • Seuils: allow/challenge/deny      │
│                                         │
│  5. Évaluation:                         │
│     • AUC-ROC                           │
│     • Precision-Recall                  │
│     • Lift curves                       │
│     • Backtesting (test set)            │
│                                         │
│  6. Métriques seuils:                   │
│     • AUC > 0.90 ✅                      │
│     • FP_rate < 2% ✅                    │
│     • TP_rate > 92% ✅                   │
│                                         │
│  7. Si OK → Export artefacts:           │
│     • model.bin (LightGBM)              │
│     • feature_pipeline.pkl              │
│     • thresholds.json                   │
│     • metadata.json (AUC, version...)   │
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         MODEL REGISTRY (MLflow)         │
│                                         │
│  Enregistrement:                        │
│  • Model version: v23                   │
│  • Stage: staging                       │
│  • Metrics: {AUC: 0.93, FP: 1.8%}       │
│  • Artefacts: {model.bin, ...}          │
│  • Git commit: abc123def                │
│                                         │
│  Validation humaine:                    │
│  • Data Scientist review                │
│  • Manager approval                     │
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         DEPLOYMENT CANARY               │
│                                         │
│  1. Deploy v23 (10% trafic)             │
│     • Pod model-serving-v23             │
│     • Route 10% via Istio               │
│                                         │
│  2. Monitoring 48h:                     │
│     • Latency P95 (< 30ms)              │
│     • Score distribution (drift)        │
│     • Decision distribution             │
│     • Error rate                        │
│                                         │
│  3. Validation métriques:               │
│     • Pas de régression latence         │
│     • Pas de drift anormal              │
│     • FP/TP rates stables               │
│                                         │
│  4. Si OK → Promote 100%                │
│     • Update all pods to v23            │
│     • MLflow: staging → production      │
│     • Archive v22 (rollback ready)      │
│                                         │
│  5. Si KO → Rollback                    │
│     • Route 100% vers v22               │
│     • Analyse root cause                │
│     • Fix et re-deploy                  │
└─────────────────────────────────────────┘

Cycle complet: 1 semaine
• Lundi: ETL + Feature engineering
• Mardi: Training + Validation
• Mercredi: Review + Approval
• Jeudi: Canary deploy 10%
• Vendredi-Lundi: Monitoring 48h
• Mardi: Promote 100%
```

---

## 🔄 Flux 5 : Observabilité (monitoring)

### Métriques → Alertes → Dashboards

```
┌─────────────────────────────────────────┐
│    SERVICES (Decision, Model, Rules)    │
│                                         │
│  Export métriques /metrics:             │
│                                         │
│  • http_request_duration_seconds        │
│    {endpoint, method, status}           │
│    Type: Histogram                      │
│                                         │
│  • fraud_score_distribution             │
│    Type: Histogram [0..1]               │
│                                         │
│  • decision_total                       │
│    {decision=ALLOW/CHALLENGE/DENY}      │
│    Type: Counter                        │
│                                         │
│  • model_inference_latency_ms           │
│    Type: Histogram                      │
│                                         │
│  • rules_evaluation_latency_ms          │
│    Type: Histogram                      │
│                                         │
│  • redis_operations_total               │
│    {operation=GET/SET}                  │
│    Type: Counter                        │
└─────────┬───────────────────────────────┘
          │
          ▼ Scrape interval: 15s
┌─────────────────────────────────────────┐
│         PROMETHEUS                      │
│                                         │
│  Collecte + Stockage time-series        │
│                                         │
│  Requêtes PromQL:                       │
│                                         │
│  • P95 latency:                         │
│    histogram_quantile(0.95,             │
│      http_request_duration_seconds)     │
│                                         │
│  • Taux decisions:                      │
│    rate(decision_total[5m])             │
│                                         │
│  • Score drift:                         │
│    stddev_over_time(                    │
│      fraud_score_distribution[1h])      │
│                                         │
│  Alertes (Alertmanager):                │
│  ┌────────────────────────────────────┐│
│  │ P95 > 120ms for 5min               ││
│  │  → PagerDuty oncall                ││
│  │                                    ││
│  │ Error_rate > 1% for 2min           ││
│  │  → Slack #fraud-alerts             ││
│  │                                    ││
│  │ Score_drift > 20% for 30min        ││
│  │  → Email data-science              ││
│  └────────────────────────────────────┘│
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│         GRAFANA                         │
│                                         │
│  Dashboard: Fraud Detection Overview    │
│  ┌────────────────────────────────────┐│
│  │ Row 1: Performance                 ││
│  │  • P50/P95/P99 latency (graph)     ││
│  │  • TPS (gauge)                     ││
│  │  • Error rate % (gauge)            ││
│  │                                    ││
│  │ Row 2: Decisions                   ││
│  │  • ALLOW/CHALLENGE/DENY (pie)      ││
│  │  • Decision trends (graph)         ││
│  │  • Taux CHALLENGE % (gauge)        ││
│  │                                    ││
│  │ Row 3: ML Model                    ││
│  │  • Score distribution (heatmap)    ││
│  │  • Model latency (graph)           ││
│  │  • Drift detection (graph)         ││
│  │                                    ││
│  │ Row 4: Infrastructure              ││
│  │  • CPU/RAM services (graph)        ││
│  │  • Postgres conn pool (gauge)      ││
│  │  • Redis memory usage (graph)      ││
│  └────────────────────────────────────┘│
│                                         │
│  Dashboard: Cases Analysts              │
│  • Cases open by queue                  │
│  • Resolution time (avg/P95)            │
│  • Analyst performance                  │
│  • Label distribution                   │
└─────────────────────────────────────────┘

Visualisation temps réel:
• Refresh: 5s
• Retention: 30 jours
• Alertes: PagerDuty/Slack/Email
```

---

## 📊 Volumétrie et performance

### Flux de données par jour (@ 10M transactions)

| Flux | Volume/jour | Latence | Stockage |
|------|-------------|---------|----------|
| **Scoring temps réel** | 10M req/resp | P95: 100ms | - |
| **Events Postgres** | 10M rows | INSERT: 10ms | ~5 GB |
| **Decisions Postgres** | 10M rows | INSERT: 10ms | ~3 GB |
| **Cases créés** | 500k (5%) | 2s | ~200 MB |
| **Features Redis** | 30M ops | 1-3ms | ~10 GB RAM |
| **Kafka events** | 20M msgs | 5ms | ~50 GB (7j) |
| **Labels ML** | 1M/jour | - | ~100 MB |
| **Metrics Prometheus** | 1M points | - | ~2 GB |

### Flux critiques (SLA)

**Synchrones** (bloquants) :
- Scoring API : P95 < 100ms
- Model inference : P95 < 30ms
- Rules evaluation : P95 < 50ms

**Asynchrones** (non-bloquants) :
- Case creation : < 5s
- Feature update : < 10s
- ML retraining : < 24h

---

## 🎯 Résumé des flux

### 5 flux principaux

1. **Scoring temps réel** (synchrone) : Transaction → Décision < 100ms
2. **Case Management** (asynchrone) : CHALLENGE/DENY → Investigation analyste
3. **Feature Store** (temps réel) : Mise à jour vélocités/flags < 5s
4. **ML Pipeline** (batch) : Labels → Retraining → Deploy (1 semaine)
5. **Observabilité** (continu) : Métriques → Alertes → Dashboards

### Patterns utilisés

- **Event Sourcing** : Toutes décisions stockées (immutable)
- **CQRS** : Séparation lecture (queries) / écriture (commands)
- **Idempotence** : Redis TTL 24h pour retry sûr
- **Circuit Breaker** : Fallback si Model/Rules timeout
- **Backpressure** : Kafka consumer groups + rate limiting

