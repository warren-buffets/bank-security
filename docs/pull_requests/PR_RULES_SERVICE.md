# Pull Request: Rules Service

## 📋 Description

Service d évaluation de règles métier avec support DSL complet pour FraudGuard AI.

## 🎯 Objectif

Service FastAPI pour évaluer des règles de détection de fraude exprimées en DSL, avec support des listes deny/allow et vélocités.

## 📦 Contenu

### Architecture

- **Rules Engine** avec DSL complet
- **Lists Checker** Redis pour deny/allow lists
- **PostgreSQL** pour stockage règles
- **Timeout 50ms** strict

### Fichiers ajoutés (1642 lignes)

- app/main.py - FastAPI app (426 lignes)
- app/rules_engine.py - Moteur DSL (335 lignes)
- app/lists_checker.py - Vérif listes (239 lignes)
- app/models.py - Pydantic models (153 lignes)
- app/config.py - Configuration (52 lignes)
- Dockerfile + requirements.txt + README.md

## 🚀 Features

### DSL Support
- ✅ Comparaisons: >, <, >=, <=, ==, !=
- ✅ Opérateurs logiques: AND, OR, NOT
- ✅ Membership: IN
- ✅ Fonctions vélocité: velocity_24h, velocity_1h

### Exemples de règles


### Endpoints
- ✅ POST /evaluate - Évaluation de transaction
- ✅ GET /health - Health check
- ✅ GET /rules - Liste règles actives
- ✅ POST /rules/reload - Refresh cache
- ✅ GET /metrics - Prometheus

### Lists Support
- ✅ Deny/Allow lists (IP, device, merchant, user, geo)
- ✅ Redis caching
- ✅ Admin functions (add/remove)

## 📊 Performance

- **Timeout**: 50ms max
- **Caching**: Règles (5min TTL), Lists (Redis)
- **Connection pooling**: PostgreSQL + Redis
- **Fail-fast**: Stop sur deny rules (optionnel)

## ✅ Tests

- [x] Code structuré
- [x] DSL parser complet
- [x] Lists checker
- [x] PostgreSQL integration
- [x] Redis caching
- [ ] Tests unitaires (à ajouter)
- [ ] Tests DSL edge cases (à ajouter)

**Branch**: feature/rules-service
**Files changed**: 9 files, 1642 insertions(+)
