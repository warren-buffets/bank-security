# SafeGuard - Documentation Index

**Plateforme de détection de fraude bancaire en temps réel**

---

## Navigation Rapide

| Objectif | Document |
|----------|----------|
| Comprendre le projet en 5 min | [GUIDE-RAPIDE.md](GUIDE-RAPIDE.md) |
| Présentation complète (soutenance) | [SIX_PAGER.md](SIX_PAGER.md) |
| Architecture technique | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Flux de données | [FLUX-DONNEES.md](FLUX-DONNEES.md) |
| Modèle ML (IEEE-CIS) | [SIX_PAGER_ML_MODEL.md](SIX_PAGER_ML_MODEL.md) |
| API Reference | [api/openapi.yaml](api/openapi.yaml) |

---

## 1. Documents Stratégiques (Six-Pagers)

### [SIX_PAGER.md](SIX_PAGER.md) - Document Principal
**Six-Pager Technique complet** (format Amazon/Microsoft)
- Résumé exécutif, contexte, design proposé
- Alternatives évaluées, risques, plan de déploiement
- **Document de soutenance**

### [SIX_PAGER_ML_MODEL.md](SIX_PAGER_ML_MODEL.md) - Modèle ML v3
**Modèle LightGBM entraîné sur IEEE-CIS**
- Dataset Vesta Corporation (590K transactions réelles)
- 12 features incluant géolocalisation IP
- AUC 0.823 (distribution équilibrée)
- Historique des versions (v1 → v3)

### [SIX_PAGER_IP_GEOLOCATION.md](SIX_PAGER_IP_GEOLOCATION.md) - Géolocalisation IP
**Feature IP avec ip-api.com**
- Cache Redis (TTL 24h)
- Calcul distance Haversine
- Métriques Prometheus

---

## 2. Documentation Technique

### [ARCHITECTURE.md](ARCHITECTURE.md)
Architecture technique complète
- 4 microservices (Decision Engine, Model Serving, Rules, Case)
- Logique de décision (ALLOW/CHALLENGE/DENY)
- Budget latence P95 < 100ms

### [FLUX-DONNEES.md](FLUX-DONNEES.md)
5 flux de données documentés
- Scoring temps réel (synchrone)
- Case Management (asynchrone)
- Feature Store, ML Training, Observabilité

### [database-schema.md](database-schema.md)
Schéma PostgreSQL
- Tables: events, decisions, cases, rules, lists
- Migrations V001-V005
- Volumétrie estimée

### [METRICS.md](METRICS.md)
Métriques ML et opérationnelles
- AUC-ROC, FPR, Precision, Recall
- Latence P95/P99, throughput

---

## 3. Architecture Decision Records (ADR)

| ADR | Sujet |
|-----|-------|
| [ADR-001](adr/001-microservices-architecture.md) | Architecture Microservices |
| [ADR-002](adr/002-redis-idempotency.md) | Redis pour l'Idempotence |
| [ADR-003](adr/003-rules-engine-dsl.md) | Moteur de Règles DSL |

---

## 4. Guides Opérationnels

### [GUIDE-RAPIDE.md](GUIDE-RAPIDE.md)
Démarrage en 3 minutes
- Installation Docker
- Test de l'API
- Comprendre les 3 décisions

### [MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md)
Commandes Makefile
- `make up`, `make down`, `make logs`
- `make db-migrate`, `make ml-train`

### [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md)
7 scripts helper
- db-helper.sh, docker-helper.sh, k8s-helper.sh
- kafka-helper.sh, ml-helper.sh, redis-helper.sh

### [IP_GEOLOCATION.md](IP_GEOLOCATION.md)
Choix technique géolocalisation
- Comparaison des options
- Solution retenue (ip-api.com + cache)

---

## 5. API

### [api/openapi.yaml](api/openapi.yaml)
Spécification OpenAPI 3.0 complète

### [api/example-requests.md](api/example-requests.md)
Exemples de requêtes/réponses

---

## 6. Services

| Service | Port | Documentation |
|---------|------|---------------|
| Decision Engine | 8000 | [README](../services/decision-engine/README.md) |
| Model Serving | 8001 | [README](../services/model-serving/README.md) |
| Rules Service | 8003 | [README](../services/rules-service/README.md) |
| Case Service | 8002 | [README](../services/case-service/README.md) |

---

## Résumé

**SafeGuard** = Détection de fraude temps réel

| Décision | Condition | Action |
|----------|-----------|--------|
| ALLOW | Score < 0.50 | Transaction autorisée |
| CHALLENGE | Score 0.50-0.70 | Demande 2FA |
| DENY | Score > 0.70 | Transaction bloquée |

**Stack**: Python FastAPI, LightGBM, PostgreSQL, Redis, Kafka, Prometheus

**Modèle ML v3**: Dataset IEEE-CIS (Vesta), AUC 0.823, 12 features
