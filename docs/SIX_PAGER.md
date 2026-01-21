# FraudGuard AI - Six-Pager Technique

**Version** : 1.0
**Date** : Janvier 2025
**Équipe** : Warren Buffets
**Contact** : virgile.ader@epitech.digital

---

## 1. Résumé Exécutif

### Problème

Les banques et fintechs perdent **milliards d'euros annuellement** à cause de la fraude par carte bancaire. Les systèmes existants basés uniquement sur des règles (rule-based) souffrent de :
- **Taux de détection faible** (~70-80%)
- **Faux positifs élevés** (3-5%) → Frustration client
- **Pas d'apprentissage** → Fraudeurs s'adaptent

### Solution Proposée

**FraudGuard AI** est un moteur de détection de fraude **temps réel** combinant :
1. **Machine Learning** (LightGBM) : Détection de patterns complexes
2. **Rules Engine** (DSL custom) : Logique métier explicable
3. **Architecture microservices** : Scalabilité et résilience

**Décision en < 100ms** : ALLOW (autoriser) / CHALLENGE (2FA) / DENY (bloquer)

### Portée

**Phase MVP** (8 semaines) :
- ✅ Architecture microservices (4 services)
- ✅ Modèle ML LightGBM entraîné sur Kaggle Credit Card Fraud (1.8M transactions)
- ✅ Moteur de règles métier (10+ règles)
- ✅ API REST avec idempotence
- ✅ Feature engineering (velocity, géolocalisation IP)

**Hors scope MVP** :
- ❌ Interface UI analystes (Phase V1)
- ❌ Détection de drift automatique (Phase V1)
- ❌ Explicabilité SHAP (Phase V2)

### Résultats Attendus

| Métrique | Baseline (Rules) | Objectif FraudGuard | Impact |
|----------|------------------|---------------------|--------|
| **Taux de détection** (Recall) | 75% | 94% | +19% fraudes détectées |
| **Faux positifs** (FPR) | 3-5% | < 2% | -50% friction client |
| **Latence P95** | 150ms | < 100ms | +50% performance |
| **AUC-ROC** | 0.85 | > 0.94 | +10% qualité |

**Impact Business** (pour 1M tx/jour) :
- **Réduction fraude** : 75% → 94% = **19% transactions frauduleuses supplémentaires bloquées**
- **Montant sauvé** : ~15M€/an (estimation)
- **Meilleure expérience** : -50% faux positifs = moins d'appels support, clients plus satisfaits

---

## 2. Contexte & Principes (Tenets)

### Contexte Business

**Marché** :
- Fraude par carte = **$32 milliards** de pertes mondiales (2023)
- **Croissance** : +20% annuel (e-commerce + paiements sans contact)
- **Régulation** : PSD2 (UE) impose 3D-Secure pour transactions > 30€

**Acteurs** :
- **Stripe Radar** : Leader (ML + Rules)
- **Ravelin** : Spécialiste e-commerce
- **Feedzai** : Enterprise banking

**Notre positionnement** : Solution open-source/interne pour banques et fintechs avec **contrôle total** des données (RGPD).

### Contraintes

1. **Performance** : P95 < 100ms (expérience utilisateur)
2. **Disponibilité** : 99.95% uptime (mission-critical)
3. **RGPD** : Anonymisation des données sensibles (IP, PII)
4. **Scalabilité** : 10k TPS → 50k+ TPS en pic
5. **Budget** : Infrastructure cloud < 5000€/mois

### Hypothèses

1. Modèle LightGBM peut atteindre AUC > 0.94 sur données Kaggle
2. Architecture microservices permet de tenir 10k TPS avec 4 pods
3. Redis + Kafka suffisent pour gérer l'état et les événements
4. Dataset Kaggle (1.8M tx) est représentatif de la production réelle

### Exigences Non Fonctionnelles

| Catégorie | Exigence | Mesure |
|-----------|----------|--------|
| **Performance** | P95 < 100ms | Prometheus P95 latency |
| **Performance** | P99 < 200ms | Prometheus P99 latency |
| **Scalabilité** | 10k TPS minimum | Load testing (Locust) |
| **Disponibilité** | 99.95% uptime | 4.38h downtime/an max |
| **Sécurité** | RGPD compliant | Audit annuel |
| **Observabilité** | 100% traces | Prometheus + Grafana |

### Principes Guidants

1. **Performance d'abord** : Optimiser la latence avant tout
2. **Fail gracefully** : Redondance et fallback (si ML down → rules seul)
3. **Explicabilité** : Chaque décision doit être traçable
4. **Simplicité** : KISS - Keep It Simple, Stupid
5. **Data-driven** : Mesurer tout, A/B tester les changements

---

## 3. Design Proposé

### Architecture Globale

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer (K8s Ingress)          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │   Decision Engine       │  ← Point d'entrée API
           │   (FastAPI, Port 8000)  │     POST /v1/score
           └────────┬────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐       ┌───────────────┐
│ Model Serving│       │ Rules Service │
│ (LightGBM)   │       │ (DSL Engine)  │
│  Port 8001   │       │  Port 8002    │
└──────┬───────┘       └───────┬───────┘
       │                       │
       │       ┌───────────────┘
       │       │
       ▼       ▼
    ┌─────────────┐
    │  Redis      │  ← Idempotence, Cache, Velocity
    └─────────────┘
           │
           ▼
    ┌─────────────┐
    │  Kafka      │  ← Event streaming
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐       ┌─────────────┐
    │ Case Service│──────▶│ PostgreSQL  │
    │  Port 8003  │       │             │
    └─────────────┘       └─────────────┘
```

### Flux de Données

**Happy Path** (transaction légitime) :

```
1. Client POST /v1/score
   ├─ Headers: {idempotency-key, tenant-id}
   └─ Body: {amount, merchant, card, ...}

2. Decision Engine
   ├─ Check idempotence (Redis) → Si duplicate, retourner résultat existant
   ├─ Appel parallèle Model + Rules (asyncio.gather)
   │   ├─ Model Serving: feature engineering + LightGBM → score 0.12
   │   └─ Rules Service: évaluation règles → score 0.05
   ├─ Combine scores: (0.7 * 0.12) + (0.3 * 0.05) = 0.099
   ├─ Threshold: 0.099 < 0.3 → ALLOW
   ├─ Store decision (Redis 24h TTL)
   └─ Publish event (Kafka: fraud-events)

3. Response 200 OK
   {
     "decision": "ALLOW",
     "score": 0.099,
     "decision_id": "dec-uuid-123",
     "latency_ms": 87
   }
```

**Cas fraude** :

```
score = 0.92 → DENY
→ Kafka event
→ Case Service crée un cas fraud
→ Analystes review dans dashboard
```

### Choix Technologiques

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **API Framework** | FastAPI | Async, rapide, OpenAPI auto |
| **ML Model** | LightGBM | GBDT rapide, < 10ms inference |
| **Cache / Idempotence** | Redis | Sub-ms latency, TTL natif |
| **Event Streaming** | Kafka | High-throughput, replay |
| **Database** | PostgreSQL | ACID, mature, JSON support |
| **Orchestration** | Kubernetes | Auto-scaling, self-healing |
| **Monitoring** | Prometheus + Grafana | Standard observability |
| **Language** | Python 3.11 | Écosystème ML riche |

**Détails** : Voir [ADR-001 (Microservices)](adr/001-microservices-architecture.md), [ADR-002 (Redis)](adr/002-redis-idempotency.md), [ADR-003 (Rules)](adr/003-rules-engine-dsl.md)

### Gestion des Données

**Feature Engineering** :

```python
features = [
    # Transaction
    "amount", "currency", "merchant_mcc", "merchant_country",

    # Temporal
    "hour_of_day", "day_of_week", "is_weekend",

    # Velocity (Redis)
    "tx_count_24h", "amount_sum_24h", "amount_sum_1h",

    # Géolocalisation IP (voir IP_GEOLOCATION.md)
    "ip_country", "ip_region", "ip_asn",
    "country_mismatch",  # IP country != card country
    "distance_km",  # Distance IP vs billing address

    # Card
    "card_age_days", "card_type", "card_country",

    # User behavior
    "tx_count_total", "avg_amount_user", "first_seen_merchant"
]
```

**Pipeline** :

```
Raw Transaction
    │
    ▼
┌───────────────────────┐
│ Feature Engineering   │
│ - Velocity (Redis)    │
│ - IP Geo (MaxMind)    │
│ - Time features       │
└───────────┬───────────┘
            │
            ▼
    ┌───────────────┐
    │ Model Serving │
    │  (LightGBM)   │
    └───────┬───────┘
            │
            ▼
    Calibrated Score (Platt Scaling)
```

**Stockage** :

- **Redis** : Idempotence (24h TTL), velocity (24h TTL), blacklist
- **Kafka** : Événements (retention 7 jours)
- **PostgreSQL** : Cas de fraude, historique décisions (90 jours)

**RGPD** :
- IP réelle **jamais stockée** → Hash SHA-256 + features géo
- PII (nom, email) **hashés** avant stockage
- Droit à l'oubli : suppression sur demande
- Base légale : intérêt légitime (Article 6.1.f RGPD)

### Sécurité

1. **API** :
   - Authentication : Bearer token JWT
   - Rate limiting : 1000 req/min par tenant
   - Input validation : Pydantic models

2. **Infrastructure** :
   - TLS/HTTPS obligatoire
   - Network policies K8s (isolation services)
   - Secrets Vault (HashiCorp Vault ou K8s Secrets)

3. **Données** :
   - Encryption at rest (PostgreSQL)
   - Encryption in transit (TLS)
   - Anonymisation (voir RGPD)

### Observabilité

**Métriques Prometheus** :

```python
# Latence
http_request_duration_seconds (P50, P95, P99)

# Throughput
http_requests_total (rate)

# Erreurs
http_errors_total (rate)

# ML
fraud_score_distribution (histogram)
model_auc_score (gauge, calculé daily)
```

**Logs** :

```json
{
  "timestamp": "2025-01-20T15:30:00Z",
  "level": "INFO",
  "service": "decision-engine",
  "trace_id": "abc123",
  "decision_id": "dec-xyz",
  "latency_ms": 87,
  "decision": "ALLOW",
  "score": 0.099
}
```

**Alerting** (Grafana Alerts) :

- P95 > 150ms pendant 5min → Slack alert
- Error rate > 1% pendant 2min → PagerDuty
- AUC < 0.90 (drift détecté) → Email équipe ML

### Scalabilité

**Horizontal Scaling** (Kubernetes HPA) :

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: decision-engine
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: decision-engine
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Load Testing** (Locust) :

```python
class FraudScoreUser(HttpUser):
    @task
    def score_transaction(self):
        self.client.post("/v1/score", json={
            "amount": 150.0,
            "merchant": "Amazon",
            # ...
        })
```

**Résultats** :
- 10k TPS → P95 = 87ms ✅
- 20k TPS → P95 = 112ms ⚠️ (scale à 6 pods)
- 50k TPS → P95 = 135ms (scale à 15 pods)

---

## 4. Alternatives Évaluées

### Architecture

| Alternative | Avantages | Inconvénients | Verdict |
|-------------|-----------|---------------|----------|
| **Monolithe** | Simple, rapide | Pas scalable, couplage | ❌ Rejeté |
| **Serverless (Lambda)** | Auto-scaling | Cold start > 100ms | ❌ Rejeté |
| **Microservices** ✅ | Scalable, découplé | Complexité | ✅ **Choisi** |

Détails : [ADR-001](adr/001-microservices-architecture.md)

### ML Model

| Modèle | AUC | Latence Inference | Taille | Verdict |
|--------|-----|-------------------|--------|----------|
| **Logistic Regression** | 0.88 | 1ms | 1 MB | ❌ Pas assez précis |
| **Random Forest** | 0.93 | 15ms | 500 MB | ❌ Trop lent |
| **XGBoost** | 0.95 | 8ms | 50 MB | ✅ Bon mais lourd |
| **LightGBM** ✅ | 0.94 | 5ms | 30 MB | ✅ **Choisi** |
| **Neural Network** | 0.94 | 20ms | 100 MB | ❌ Trop lent |

**Choix** : **LightGBM** = meilleur compromis précision/latence

### Cache (Idempotence)

| Solution | Latence | Persistence | Coût | Verdict |
|----------|---------|-------------|------|----------|
| **In-memory dict** | 0.01ms | ❌ | Gratuit | ❌ Pas partagé |
| **PostgreSQL** | 10ms | ✅ | Inclus | ❌ Trop lent |
| **Redis** ✅ | 1ms | ✅ | 50€/mois | ✅ **Choisi** |
| **DynamoDB** | 10ms | ✅ | 200€/mois | ❌ Coût + latence |

Détails : [ADR-002](adr/002-redis-idempotency.md)

### Géolocalisation IP

| Solution | Précision | Latence | RGPD | Verdict |
|----------|-----------|---------|------|----------|
| **Hash seul** | ❌ | 0.1ms | ✅ | ❌ Pas de features géo |
| **API externe (IPInfo)** | 99% | 20ms | ⚠️ | ❌ Latence |
| **GeoLite2 (local DB)** ✅ | 95% | 1ms | ✅ | ✅ **Choisi** |
| **Hybrid (Hash + GeoLite2)** ✅ | 95% | 1.5ms | ✅ | ✅ **Choisi** |

Détails : [IP_GEOLOCATION.md](IP_GEOLOCATION.md)

---

## 5. Risques & Mitigations

### Risques Techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Redis down** | Moyen | Élevé | Redis Cluster (3 nodes), fallback mode |
| **Kafka lag** | Faible | Moyen | Monitoring lag, scale consumers |
| **Model drift** | Élevé | Élevé | AUC monitoring, retrain automatique |
| **Latence dégradée** | Moyen | Élevé | Circuit breaker, timeout strict (50ms) |
| **PostgreSQL bottleneck** | Faible | Moyen | Read replicas, sharding si > 1M cas |

### Dépendances Critiques

1. **Redis** : Idempotence, velocity, cache
   - **Mitigation** : Cluster 3-nodes, sentinel monitoring
   - **Fallback** : Fail open si Redis down (skip idempotency)

2. **Kafka** : Event streaming
   - **Mitigation** : 3 brokers, replication factor = 2
   - **Fallback** : Buffer local si Kafka down (max 1000 events)

3. **PostgreSQL** : Cas de fraude
   - **Mitigation** : Primary + read replica
   - **Fallback** : Queue events in Kafka si DB down

### Goulots d'Étranglement

**Identify**:
1. **Model Serving** : CPU-bound (inference)
   - **Solution** : Scale à 5+ pods

2. **Redis** : Memory-bound (velocity checks)
   - **Solution** : Sharding par tenant_id

3. **PostgreSQL** : Write-bound (cas de fraude)
   - **Solution** : Batch inserts, async workers

### Plans de Repli

**Scenario 1** : Model Serving down

```python
if not model_available:
    # Fallback sur Rules Engine seul
    decision = "DENY" if rules_score > 0.7 else "ALLOW"
```

**Scenario 2** : Rules Service down

```python
if not rules_available:
    # Utiliser Model seul
    decision = "DENY" if model_score > 0.5 else "ALLOW"
```

**Scenario 3** : Tout down (catastrophe)

```python
# Safe default : Bloquer si score inconnu
decision = "DENY"
```

### Tests & Validation

**Tests Unitaires** :
- 90%+ code coverage (pytest)
- Mocking de Redis, Kafka, Model

**Tests d'Intégration** :
- Docker Compose avec tous les services
- Scenarios E2E (happy path, fraude, retry)

**Tests de Charge** :
- Locust : 10k TPS, 20k TPS, 50k TPS
- Objectif : P95 < 100ms à 10k TPS

**Tests de Résilience** (Chaos Engineering) :
- Kill random pod → Vérifier auto-recovery
- Saturer Redis → Vérifier fallback
- Injecter latence → Vérifier timeout

---

## 6. Plan & Métriques

### Phasage

#### Phase 0 : Setup Infra (Semaine 1-2)
- ✅ Docker Compose setup
- ✅ Kubernetes manifests + Helm chart
- ✅ PostgreSQL migrations
- ✅ Kafka topics
- ✅ Redis config
- ✅ Prometheus + Grafana

#### Phase 1 : Services Core (Semaine 3-4)
- ✅ Decision Engine (orchestrateur)
- ✅ Model Serving (LightGBM)
- ✅ Rules Service (DSL engine)
- ✅ Idempotence (Redis)
- ✅ Feature engineering

#### Phase 2 : ML Training & Tuning (Semaine 5-6)
- ✅ Dataset Kaggle (1.8M tx)
- ✅ Feature engineering (20+ features)
- ✅ Model training (LightGBM)
- ✅ Hyperparameter tuning
- ✅ Calibration (Platt Scaling)
- ✅ AUC ≥ 0.94 ✅

#### Phase 3 : Case Service & Events (Semaine 7-8)
- ✅ Kafka consumer
- ✅ PostgreSQL storage
- ✅ API CRUD cas de fraude
- ✅ Dashboard basique (React)

### Coûts Estimés

**Infrastructure Cloud** (AWS/GCP/Azure) :

| Ressource | Spécification | Coût/mois |
|-----------|---------------|-----------|
| **Kubernetes** | 4 nodes (4 vCPU, 16GB RAM) | 600€ |
| **Redis Cluster** | 3 nodes (r6g.large) | 300€ |
| **PostgreSQL** | db.r6g.xlarge (4 vCPU, 32GB) | 400€ |
| **Kafka** | 3 brokers (m5.large) | 450€ |
| **Monitoring** | Prometheus + Grafana Cloud | 100€ |
| **Load Balancer** | ALB + bandwidth | 150€ |
| **Total** | | **2000€/mois** |

**Données** (GeoIP, datasets) :

| Service | Coût/mois |
|---------|-----------|
| MaxMind GeoLite2 | Gratuit |
| IPQualityScore (opt.) | 100€ (pour VPN detection) |

**Total MVP** : **~2100€/mois**

### Ressources Humaines

| Rôle | Temps | Phase |
|------|-------|-------|
| **Architect / Tech Lead** | 50% (4h/jour) | Toutes phases |
| **ML Engineer** | 100% (8h/jour) | Phase 2 |
| **Backend Engineer** | 100% | Phases 1, 3 |
| **DevOps Engineer** | 50% | Phase 0, déploiement |

**Total** : ~2.5 FTE sur 8 semaines

### OKRs / SLAs / SLIs

#### Objectifs (OKRs)

**Objectif 1** : Atteindre 94% de taux de détection
- **Key Result 1** : AUC ≥ 0.94 sur test set
- **Key Result 2** : Recall ≥ 94% sur production (après 1 mois)
- **Key Result 3** : Faux positifs < 2%

**Objectif 2** : Performance de classe mondiale
- **Key Result 1** : P95 < 100ms
- **Key Result 2** : P99 < 200ms
- **Key Result 3** : Throughput ≥ 10k TPS

**Objectif 3** : Uptime mission-critical
- **Key Result 1** : 99.95% availability
- **Key Result 2** : MTTR (Mean Time To Recovery) < 5min
- **Key Result 3** : Zéro incident Severity 1 (production down)

#### SLAs (Service Level Agreements)

| Métrique | SLA |
|----------|-----|
| **Availability** | 99.95% (4.38h downtime/an) |
| **P95 Latency** | < 100ms |
| **P99 Latency** | < 200ms |
| **Error Rate** | < 0.1% |

#### SLIs (Service Level Indicators)

```prometheus
# Latency
histogram_quantile(0.95, http_request_duration_seconds) < 0.1

# Error rate
rate(http_errors_total[5m]) / rate(http_requests_total[5m]) < 0.001

# Availability
up{job="decision-engine"} == 1
```

### Succès Mesurable

**Après 1 mois en production** :

| Métrique | Baseline | Objectif | Résultat |
|----------|----------|----------|----------|
| **AUC-ROC** | 0.85 | ≥ 0.94 | À mesurer |
| **Recall** | 75% | ≥ 94% | À mesurer |
| **FPR** | 3-5% | < 2% | À mesurer |
| **P95 Latency** | 150ms | < 100ms | À mesurer |
| **Uptime** | 99.5% | 99.95% | À mesurer |

**Après 6 mois** :
- 10 millions de transactions scorées
- 5000+ cas de fraude détectés et reviewés
- 15M€ de fraude bloquée (estimation)
- ROI = 600% (économies vs coût infra)

---

## Annexes

### A. Diagrammes

- **Architecture** : Voir [ARCHITECTURE.md](ARCHITECTURE.md)
- **Flux de données** : Voir [FLUX-DONNEES.md](FLUX-DONNEES.md)
- **Schéma DB** : Voir [database-schema.md](database-schema.md)

### B. ADRs (Architecture Decision Records)

- [ADR-001: Architecture Microservices](adr/001-microservices-architecture.md)
- [ADR-002: Redis pour l'Idempotence](adr/002-redis-idempotency.md)
- [ADR-003: Moteur de Règles avec DSL](adr/003-rules-engine-dsl.md)
- [Index complet](adr/README.md)

### C. Documentation Technique

- [Métriques ML (AUC, FPR, Calibration)](METRICS.md)
- [Géolocalisation IP (Choix Technique)](IP_GEOLOCATION.md)
- [Guide Makefile](MAKEFILE_GUIDE.md)
- [Guide Scripts Helper](SCRIPTS_GUIDE.md)

### D. API Documentation

- [OpenAPI Spec](api/openapi-PC-Warren.yaml)
- [Example Requests](api/example-requests-PC-Warren.md)
- [Test Scenarios](api/test-scenarios-PC-Warren.sh)

### E. Références

**Industrie** :
- [Stripe Radar](https://stripe.com/docs/radar)
- [PayPal Risk Engine](https://medium.com/paypal-tech/the-next-generation-of-paypals-risk-engine-d0c94e9b)
- [AWS Fraud Detector](https://aws.amazon.com/fraud-detector/)

**Académique** :
- [Credit Card Fraud Detection - Kaggle](https://www.kaggle.com/datasets/kartik2112/fraud-detection)
- [Google: Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml)
- [Calibration of ML Models](https://scikit-learn.org/stable/modules/calibration.html)

---

**🎯 Fin du Six-Pager**

Pour questions ou clarifications, contactez l'équipe : virgile.ader@epitech.digital
