# Pull Request: Decision Engine Service

## 📋 Description

Orchestrateur principal de FraudGuard AI qui coordonne l analyse de fraude en temps réel.

## 🎯 Objectif

Service FastAPI qui orchestre les appels parallèles au Model Serving et Rules Service, implémente l idempotence, stocke les décisions et publie les événements.

## 📦 Contenu

### Architecture

- **Orchestrateur** avec appels parallèles (asyncio)
- **Idempotence** Redis (24h TTL)
- **Storage** PostgreSQL (events + decisions)
- **Event publishing** Kafka
- **Decision logic** intelligente avec support 2FA

### Fichiers ajoutés (1574 lignes)

- app/main.py - FastAPI app (295 lignes)
- app/orchestrator.py - Logique orchestration (249 lignes)
- app/storage.py - PostgreSQL (202 lignes)
- app/kafka_producer.py - Events Kafka (144 lignes)
- app/idempotency.py - Redis idempotence (102 lignes)
- app/models.py - Pydantic models (84 lignes)
- app/config.py - Configuration (80 lignes)
- Dockerfile + requirements.txt + README.md

## 🚀 Features

- ✅ POST /v1/score - Endpoint principal de scoring
- ✅ Appels parallèles Model Serving + Rules Service
- ✅ Idempotence Redis avec TTL 24h
- ✅ Logique décision intelligente ALLOW/CHALLENGE/DENY
- ✅ Support 2FA (pas de doublon si déjà validé)
- ✅ Storage PostgreSQL (events + decisions immuables)
- ✅ Publishing Kafka (decision_events + case_events)
- ✅ Prometheus metrics
- ✅ Health checks

## 🎯 Logique de décision

- Score < 0.50 → ALLOW
- Score 0.50-0.70 + pas de 2FA → CHALLENGE (demander 2FA)
- Score 0.50-0.70 + 2FA présent → ALLOW (2FA suffit)
- Score > 0.70 → CHALLENGE/DENY
- Règles critiques → DENY immédiat

## 📊 Performance

- **Budget latence**: 15ms orchestration
- **Timeout Model Serving**: 30ms
- **Timeout Rules Service**: 50ms
- **Total P95**: < 100ms
- **Throughput cible**: 10k TPS

## ✅ Tests

- [x] Code structuré et documenté
- [x] Endpoints implémentés
- [x] Orchestration parallèle
- [x] Idempotence Redis
- [x] Storage PostgreSQL
- [ ] Tests unitaires (à ajouter)
- [ ] Tests d intégration (à ajouter)

**Branch**: feature/decision-engine
**Files changed**: 10 files, 1574 insertions(+)
