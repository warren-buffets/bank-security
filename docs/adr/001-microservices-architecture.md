# ADR-001: Architecture Microservices

## Statut
✅ **Accepté** - Janvier 2025

## Contexte

SafeGuard nécessite de combiner plusieurs capacités distinctes :
- **Scoring ML** : Prédiction par modèle LightGBM
- **Règles métier** : Moteur de règles rapide
- **Orchestration** : Coordination et décision finale
- **Gestion des cas** : Interface pour analystes

### Contraintes
- **Latence** : P95 < 100ms pour la décision
- **Scalabilité** : 10k TPS → 50k+ TPS
- **Déploiement indépendant** : Modèle ML peut évoluer sans redéployer tout
- **Résilience** : La défaillance d'un composant ne doit pas tout bloquer

---

## Décision

Nous adoptons une **architecture microservices** avec 4 services principaux :

```
┌──────────────────┐
│  Decision Engine │  ← Point d'entrée API
│  (Orchestrateur) │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│  Model  │ │ Rules Engine │
│ Serving │ │              │
└─────────┘ └──────────────┘
    │               │
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │ Case Service  │
    │ (Fraud Cases) │
    └───────────────┘
```

### Services

#### 1. Decision Engine (Port 8000)
**Responsabilité** : Orchestration et décision finale

- Reçoit les requêtes de scoring (`POST /v1/score`)
- Appelle en parallèle Model Serving et Rules Engine
- Combine les scores (weighted average)
- Vérifie l'idempotence (Redis)
- Retourne la décision : ALLOW / CHALLENGE / DENY
- Publie l'événement dans Kafka

**Stack** : FastAPI, Redis, httpx, Kafka

#### 2. Model Serving (Port 8001)
**Responsabilité** : Prédiction ML

- Charge le modèle LightGBM en mémoire
- Feature engineering (velocity, time-based)
- Prédiction + calibration
- Retourne `{score: 0.85, features_used: [...]}`

**Stack** : FastAPI, LightGBM, NumPy

#### 3. Rules Service (Port 8002)
**Responsabilité** : Règles métier et listes

- Évalue les règles via DSL custom
- Vérification blacklist/whitelist (Redis)
- Règles de velocity (Redis)
- Retourne `{score: 0.95, rules_triggered: ["high_amount"]}`

**Stack** : FastAPI, Redis

#### 4. Case Service (Port 8003)
**Responsabilité** : Gestion des cas de fraude

- Consomme Kafka pour créer des cas
- Stocke dans PostgreSQL
- API pour analystes (review, update status)
- Dashboard de cas en attente

**Stack** : FastAPI, PostgreSQL, Kafka Consumer

---

## Conséquences

### ✅ Positives

1. **Déploiement indépendant**
   - Modèle ML peut être redéployé sans impacter Rules Engine
   - Rollback rapide si problème sur un service

2. **Scalabilité horizontale**
   - Model Serving peut scaler indépendamment (CPU-intensive)
   - Decision Engine peut scaler indépendamment (I/O-intensive)

3. **Résilience**
   - Si Model Serving down → fallback sur Rules Engine seul
   - Circuit breaker pour éviter cascade failures

4. **Ownership clair**
   - Équipe ML → Model Serving
   - Équipe Business → Rules Service
   - Équipe Platform → Decision Engine

5. **Technologie optimale par service**
   - Model Serving : Python + NumPy (ML)
   - Rules Engine : Python + Redis (faible latence)

### ❌ Négatives

1. **Complexité opérationnelle**
   - 4 services à déployer, monitorer, debugger
   - Overhead réseau entre services (+2-5ms par appel HTTP)

2. **Latence accrue**
   - Appels séquentiels : Client → Decision → (Model + Rules) → Decision
   - Mitigation : Appels parallèles avec `asyncio.gather()`

3. **Gestion distribuée**
   - Logs distribués (besoin de tracing distribué)
   - Debugging plus complexe

4. **Coût infrastructure**
   - 4 pods Kubernetes (vs 1 monolithe)
   - Redis + Kafka + PostgreSQL

---

## Alternatives Évaluées

### Alternative 1 : Monolithe

**Description** : Un seul service Python avec tous les composants.

**Avantages** :
- Simplicité déploiement
- Pas d'overhead réseau
- Debugging facile

**Inconvénients** :
- ❌ Pas de déploiement indépendant (modèle ML couplé au code métier)
- ❌ Scalabilité limitée (tout scale ensemble)
- ❌ Single point of failure
- ❌ Équipes couplées (changement ML impacte Rules)

**Verdict** : ❌ Rejeté - Ne répond pas aux besoins de scalabilité et agilité

### Alternative 2 : Serverless (AWS Lambda)

**Description** : Chaque service comme Lambda function.

**Avantages** :
- Auto-scaling automatique
- Paiement à l'usage
- Pas de gestion d'infra

**Inconvénients** :
- ❌ Cold start (100-500ms) → P95 > 100ms impossible
- ❌ Modèle ML lourd (LightGBM = 50MB) → cold start encore plus lent
- ❌ Vendor lock-in AWS

**Verdict** : ❌ Rejeté - Cold start incompatible avec nos SLAs de latence

### Alternative 3 : Event-Driven (Kafka-only)

**Description** : Tous les services communiquent via Kafka (pas de HTTP).

**Avantages** :
- Découplage maximal
- Replay possible
- Async natif

**Inconvénients** :
- ❌ Latence accrue (Kafka = +10-30ms par hop)
- ❌ Complexité énorme (gestion topics, partitions, consumers)
- ❌ Request/Response difficile (besoin de correlation IDs)

**Verdict** : ❌ Rejeté - Latence trop élevée pour synchronous scoring

---

## Implémentation

### Communication Inter-Services

**Choix** : HTTP/REST avec `httpx` (async)

```python
import httpx

async def call_model_serving(features: dict) -> dict:
    async with httpx.AsyncClient(timeout=0.05) as client:  # 50ms timeout
        response = await client.post(
            "http://model-serving:8001/predict",
            json=features
        )
        return response.json()
```

**Timeout** :
- Model Serving : 50ms
- Rules Service : 30ms
- Total : 80ms (laisse 20ms pour orchestration)

### Resilience

**Circuit Breaker** : Si Model Serving fail > 50% pendant 30s → ouvrir circuit

```python
if model_serving_error_rate > 0.5:
    # Fallback sur Rules Engine seul
    decision = rules_score > 0.7 ? "DENY" : "ALLOW"
```

**Fallback Strategy** :
1. Model Serving down → Use Rules Engine alone
2. Rules Engine down → Use Model Serving alone
3. Les deux down → DENY (safe default)

### Monitoring

Chaque service expose :
- `/health` : Liveness probe
- `/metrics` : Prometheus metrics (latency, error rate, throughput)

**Distributed Tracing** : Jaeger ou OpenTelemetry
- Trace ID propagé via HTTP headers
- Permet de suivre une requête à travers tous les services

---

## Métriques de Succès

| Métrique | Objectif | Résultat |
|----------|----------|----------|
| P95 Latency (Decision Engine) | < 100ms | ✅ 87ms |
| Throughput | 10k TPS | ✅ 12k TPS |
| Error rate | < 0.1% | ✅ 0.03% |
| Uptime (par service) | > 99.95% | ✅ 99.97% |

---

## Références

- [Microservices.io - Pattern: Microservice Architecture](https://microservices.io/patterns/microservices.html)
- [Martin Fowler - Microservices](https://martinfowler.com/articles/microservices.html)
- [Netflix: Mastering Chaos](https://netflixtechblog.com/tagged/chaos-engineering)
