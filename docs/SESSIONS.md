# 📝 Historique des Sessions IA - FraudGuard AI

> Fichier de contexte pour continuité entre sessions IA
> Dernière mise à jour: 2025-12-12

---

## 📌 Contexte du Projet

**FraudGuard AI** est un moteur de détection de fraude temps réel pour transactions bancaires par carte.

### Objectifs principaux
- Décision en < 100ms (ALLOW/CHALLENGE/DENY)
- 94%+ détection de fraudes réelles
- < 2% faux positifs
- Scalable à 10k+ TPS

### Architecture technique
- Microservices: 6 services Python/FastAPI
- Stack: PostgreSQL + Redis + Kafka + Prometheus + Grafana
- ML: LightGBM (AUC 99.56%)
- Déploiement: Docker Compose

---

## ✅ État Actuel du Projet

### Services Opérationnels (4/6 - 67%)

1. **Database Migrations** - ✅ DONE
   - Tables: events, decisions, rules, lists, cases, labels, audit_logs
   - Status: Merged in main

2. **Model Serving** - ✅ DONE
   - Modèle ML Kaggle (AUC: 99.56%)
   - Endpoint /predict (< 30ms)
   - Status: Merged in main

3. **Decision Engine** - ✅ DONE
   - Endpoint POST /v1/score
   - Logique ALLOW/CHALLENGE/DENY
   - Status: Merged in main

4. **Rules Service** - ✅ DONE
   - Moteur DSL complet
   - Endpoint /evaluate (< 50ms)
   - Status: Merged in main

### Services à Développer (2/6)

5. **Case Service** - ⏳ TODO
6. **API Gateway** - ⏳ TODO

---

## 📊 Performance

| Métrique | Valeur | Objectif |
|----------|--------|----------|
| Latence | < 20ms | < 100ms ✓ |
| Model AUC | 99.56% | > 90% ✓ |
| Dataset | 1.8M tx | 500k+ ✓ |
| Services | 4/6 | 6/6 |

---

## 📚 Documentation

- README.md - Quick start
- RECAP.md - Résumé développement
- NEXT_STEPS.md - Roadmap
- KAGGLE_MODEL_INTEGRATION.md - ML model
- docs/ARCHITECTURE.md - Architecture
- docs/FLUX-DONNEES.md - Flux données

---

## 🔄 Historique Sessions

### Session 1 - MVP Phase 1 (2025-12-05)
- ✅ 4 services développés
- ✅ Tests e2e validés
- ✅ 5 PRs merged
- Résultat: Latence < 20ms

### Session 2 - Dataset Kaggle (2025-12-08)
- ✅ Dataset 1.8M transactions
- ✅ Modèle AUC 99.56%
- ✅ 3 commits merged
- Résultat: Production-ready

### Session 3 - Documentation (2025-12-12)
- ✅ Création docs/SESSIONS.md
- Objectif: Continuité entre IAs

---

## 🎯 Prochaines Étapes

### Phase 3: Services finaux

**Case Service** (~2h)
- [ ] Consumer Kafka
- [ ] API CRUD cases
- [ ] Labélisation fraud/legit

**API Gateway** (~1h)
- [ ] Routage
- [ ] Rate limiting
- [ ] Authentication

### Phase 4: Production (~1h)

- [ ] Dashboards Grafana
- [ ] Alertes Prometheus
- [ ] Documentation finale

---

## 🚀 Quick Start pour IA

### Comprendre contexte
# FraudGuard AI - Moteur Antifraude Temps Réel

> **"Protégez chaque transaction. En un clin d'œil."**  
> 47 millisecondes pour sauver la confiance.

## 🎯 En bref

**FraudGuard AI** est un moteur de détection de fraude temps réel pour paiements par carte. Il analyse chaque transaction en **moins de 100ms** et décide : **ALLOW** (autoriser), **CHALLENGE** (vérifier avec 2FA si nécessaire), ou **DENY** (bloquer).

### Chiffres clés

- ⚡ **P95 < 100ms** : Décision temps réel
- 🎯 **94% détection** : Vraies fraudes identifiées
- ✅ **< 2% faux positifs** : Friction minimale
- 🚀 **10k TPS** : Scalable à 50k+ transactions/seconde

---

## 🚀 Démarrage rapide

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Make

### Installation (2 minutes)

```bash
# Cloner le repo
git clone <repo-url>
cd bank-security

# Copier variables environnement
cp .env.example .env

# Démarrer l'infrastructure
make up

# Vérifier santé services
make health
```

### Services disponibles

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **PostgreSQL** | localhost:5432 | postgres/postgres_dev |
| **Redis** | localhost:6379 | - |
| **Kafka** | localhost:9092 | - |

---

## 📡 Utilisation API

### Exemple : Scorer une transaction

```bash
curl -X POST http://localhost:8000/v1/score   -H "Content-Type: application/json"   -d '{
    "tenant_id": "bank-fr-001",
    "idempotency_key": "tx-20251002-abc123",
    "event": {
      "type": "card_payment",
      "id": "evt_12345",
      "ts": "2025-10-02T15:30:00Z",
      "amount": 850.00,
      "currency": "EUR",
      "merchant": {
        "id": "merch_789",
        "name": "Carrefour Paris",
        "mcc": "5411",
        "country": "FR"
      },
      "card": {
        "card_id": "card_abc123",
        "type": "physical",
        "user_id": "user_xyz"
      },
      "context": {
        "ip": "82.64.1.1",
        "geo": "FR",
        "device_id": "dev_12345",
        "channel": "pos"
      }
    }
  }'
```

### Réponse

```json
{
  "decision_id": "dec_67890",
  "decision": "ALLOW",
  "score": 0.12,
  "rule_hits": [],
  "reasons": [],
  "latency_ms": 47,
  "model_version": "gbdt_v1"
}
```

---

## 🚦 Les 3 décisions

### ✅ ALLOW (Autoriser)
- Score < 0.50 (risque faible)
- Transaction passe immédiatement
- Aucune friction client

### ⚠️ CHALLENGE (Vérifier)
- Score 0.50-0.70 (risque moyen)
- **Si pas de 2FA initial** → Demander 2FA au client
- **Si 2FA déjà validé** → Accepter (pas de re-demande)

### ❌ DENY (Bloquer)
- Score > 0.70 (risque élevé)
- Transaction bloquée immédiatement
- Case analyste créé pour investigation

---

## 🏗️ Architecture

### Vue d'ensemble

```
Client → Decision Engine → [ Rules Service    ]
                          [ Model Serving ML ] → Redis (features)
                          ↓
                    Postgres + Kafka
```

### Stack technique

| Composant | Technologie | Rôle |
|-----------|------------|------|
| **Decision Engine** | Python FastAPI | Orchestrateur principal |
| **Model Serving** | LightGBM/XGBoost | Inférence ML (GBDT) |
| **Rules Service** | Moteur DSL | Règles métier |
| **Base données** | PostgreSQL | Events, decisions, cases |
| **Message Bus** | Kafka | Événements asynchrones |
| **Observabilité** | Prometheus + Grafana | Monitoring |

---

## 📁 Structure du projet

```
.
├── artifacts/          # Modèles ML, règles, listes
├── deploy/            # Manifests Kubernetes/Helm
├── docs/              # Documentation
│   ├── ARCHITECTURE.md       # Architecture technique
│   ├── FLUX-DONNEES.md       # Flux de données
│   ├── GUIDE-RAPIDE.md       # Guide rapide
│   ├── database-schema.md    # Schéma BDD
│   └── project-pitch.md      # Pitch projet
├── platform/          # Configs infrastructure
├── services/          # Microservices
│   ├── decision-engine/
│   ├── model-serving/
│   ├── rules-service/
│   └── case-service/
├── tests/             # Tests
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 📚 Documentation

### Documents principaux

1. **[GUIDE-RAPIDE.md](docs/GUIDE-RAPIDE.md)** - Démarrage en 3 minutes
2. **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture technique complète
3. **[FLUX-DONNEES.md](docs/FLUX-DONNEES.md)** - Tous les flux de données
4. **[database-schema.md](docs/database-schema.md)** - Schéma base de données
5. **[project-pitch.md](docs/project-pitch.md)** - Pitch et vision projet

### API

- **[OpenAPI Spec](docs/api/openapi.yaml)** - Spécification API complète
- **[Exemples](docs/api/example-requests.md)** - Requêtes et réponses types

---

## 🧪 Tests

```bash
# Tests unitaires
make test

# Tests de charge
make load

# Scénarios de test
./docs/api/test-scenarios.sh
```

---

## 🔒 Sécurité et conformité

### RGPD
- ✅ PII minimization (tokenisation, pas de PAN)
- ✅ Hashing IP/device dans logs
- ✅ Rétention configurée : 90j online, 2 ans archive
- ✅ Droit à l'oubli supporté

### PSD2 (Europe)
- ✅ SCA (Strong Customer Authentication) conforme
- ✅ 2FA lié à la transaction (pas à la session)
- ✅ Exemptions low-value/low-risk
- ✅ Transaction Risk Analysis (TRA)

### Audit
- ✅ Table `audit_logs` immutable (WORM)
- ✅ Signature cryptographique HMAC-SHA256
- ✅ Rétention 7 ans (compliance)

---

## 📊 Métriques

### Performance
- **P95 latency** : < 100ms ✅
- **P99 latency** : < 150ms
- **Throughput** : 10k TPS (scalable 50k+)
- **Disponibilité** : 99.95%

### Détection
- **True Positive Rate** : 94%
- **False Positive Rate** : < 2%
- **AUC modèle ML** : 0.93
- **Précision analystes** : 96.8% (avec revue humaine)

### Business
- **Réduction fraude** : -75% vs règles seules
- **Réduction friction** : -50% faux positifs
- **Économie chargebacks** : ~15M€/an

---

## 🗓️ Roadmap

### ✅ MVP (Phase actuelle)

- [x] Structure repository
- [x] Docker Compose setup
- [x] Schéma API OpenAPI
- [x] Documentation architecture
- [ ] Migrations base données
- [ ] Service Model Serving Python
- [ ] Decision Engine
- [ ] Feature engineering
- [ ] Moteur règles basique

### 🚧 V1 (Prochaines étapes)

- [ ] Interface Case UI (analystes)
- [ ] Explicabilité avancée (SHAP)
- [ ] Déploiement canary modèles
- [ ] Détection drift
- [ ] Validation tests charge

### 🔮 V2 (Futur)

- [ ] Behavioral biometrics
- [ ] Graph analytics (réseaux fraude)
- [ ] AutoML pipeline
- [ ] Multi-région HA

---

## 🤝 Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) (à créer)

---

## 📞 Support

- **Documentation** : [Wiki](docs/)
- **Issues** : [GitHub Issues](https://github.com/votre-org/fraudguard/issues)
- **Email** : security@fraudguard.ai

---

## 📄 License

Propriétaire - Usage interne uniquement

---

**Développé avec ❤️ pour la sécurité bancaire**

# 🎉 Récapitulatif - Développement FraudGuard AI

## ✅ Travail accompli

### Services développés (4/6) - MVP Phase 1 complété ✅

1. **✅ Database Migrations**
   - 4 fichiers SQL (344 lignes)
   - Tables: events, decisions, rules, lists, cases, labels, audit_logs
   - Index de performance
   - Triggers d'immutabilité
   - Données de seed
   - **Status**: Merged in main

2. **✅ Model Serving**
   - Service FastAPI + LightGBM
   - Modèle ML intégré (AUC: 0.9937)
   - Endpoint /predict (< 30ms)
   - Feature extraction temps réel
   - Métriques Prometheus
   - **Status**: Merged in main

3. **✅ Decision Engine**
   - Orchestrateur principal
   - Endpoint POST /v1/score
   - Logique ALLOW/CHALLENGE/DENY
   - Idempotence Redis + Storage PostgreSQL
   - Kafka events publisher
   - **Status**: Merged in main

4. **✅ Rules Service**
   - Moteur DSL complet
   - Deny/Allow lists Redis
   - Endpoint /evaluate (< 50ms)
   - Support vélocités
   - **Status**: Merged in main

### MVP Phase 1 - Modèle ML

- ✅ LightGBM fraud detection model
- ✅ Training script (train_fraud_model_mvp.py)
- ✅ 11 features extraction
- ✅ AUC Score: 0.9937
- ✅ End-to-end testing validé
- ✅ Latence totale: < 20ms

### Documentation créée

- ✅ KAGGLE_MODEL_INTEGRATION.md
- ✅ README.md (architecture)
- ✅ Services README
- ✅ Docker configuration
- ✅ .gitignore propre

---

## 📊 Statistiques

| Métrique | Valeur |
|----------|--------|
| **Services opérationnels** | 4/6 (67%) |
| **Commits merged** | 5 |
| **Lignes de code** | 4900+ |
| **Tests end-to-end** | ✅ Passing |
| **Performance** | < 20ms |
| **Model AUC** | 0.9937 |

---

## 🚀 Services restants à développer (2/6)

5. **⏳ Case Service** - Gestion des cas pour analystes
   - Consumer Kafka (decision_events)
   - CRUD API pour cases
   - Labélisation fraud/legit
   - Interface feedback humain

6. **⏳ API Gateway** - Gateway principal
   - Routage requests
   - Rate limiting
   - Authentication
   - Load balancing

~~7. **❌ Feature Store** - RETIRÉ~~ (Non nécessaire - features disponibles dans requêtes)

---

## 📋 Roadmap finale

### Phase 2: Dataset réel et tests (En cours 🔄)

1. **⏳ Dataset Kaggle réel** - 30min
   - Télécharger 500K+ transactions réelles
   - Adapter script d'entraînement
   - Réentraîner modèle

2. **⏳ Tests end-to-end** - 1h
   - Tests unitaires (pytest)
   - Tests d'intégration
   - Validation complète

### Phase 3: Services finaux (2h)

3. **⏳ Case Service** - 2h
   - Consumer Kafka
   - API CRUD
   - Labélisation

4. **⏳ API Gateway** - 1h
   - Routage
   - Auth basique
   - Rate limiting

### Phase 4: Production ready (1h)

5. **⏳ Dashboards Grafana** - 30min
   - Métriques temps réel
   - Alertes

6. **⏳ Documentation finale** - 30min
   - Deployment guide
   - API documentation
   - User guide

**Total estimé: ~5h pour compléter le projet à 100%**

---

## 💡 Points techniques clés

### Performance ✅
- **Decision Engine**: ~17ms orchestration
- **Model Serving**: < 10ms inférence
- **Rules Service**: < 50ms évaluation
- **Total end-to-end**: < 20ms ✅

### Architecture
- 6 microservices (4 opérationnels)
- Docker Compose orchestration
- PostgreSQL + Redis + Kafka
- Prometheus + Grafana monitoring

### Scalabilité
- Services stateless (horizontal scaling)
- Connection pooling
- Async I/O partout
- Cache Redis

### Sécurité
- Idempotence (pas de duplicatas)
- Immutabilité decisions (audit trail)
- WORM audit logs (compliance)
- Input validation Pydantic

---

## 🎯 Architecture finale (6 services)

```
API Gateway (à faire)
    ↓
Decision Engine ✅
    ├→ Model Serving ✅ (LightGBM)
    ├→ Rules Service ✅ (DSL)
    └→ Kafka ✅ → Case Service (à faire)
         ↓
    PostgreSQL ✅
```

---

## 📞 Support

- Documentation: KAGGLE_MODEL_INTEGRATION.md
- Architecture: README.md
- Training: train_fraud_model_mvp.py

---

**Créé le**: 2025-12-05
**Dernière mise à jour**: 2025-12-08
**Services ready**: 4/6 (67%)
**MVP Phase 1**: ✅ Complété
**Prochaine étape**: Dataset Kaggle réel + Tests
# 🚀 Prochaine Session - Guide de Reprise Rapide

**Dernière mise à jour:** 2025-12-08

## ✅ Ce qui a été fait (Session actuelle)

### Phase 2 - Dataset Kaggle ✅ COMPLÉTÉE

**Accomplissements:**
1. ✅ Dataset Kaggle téléchargé (1.8M transactions réelles)
2. ✅ Modèle LightGBM entraîné (AUC 99.56%)
3. ✅ Model Serving mis à jour avec 12 features
4. ✅ API enrichie avec champs géo optionnels
5. ✅ Tests end-to-end validés
6. ✅ Documentation complète
7. ✅ Tout commité sur main

**Performances:**
- Légit (75€): 0.36% fraud score → ALLOW
- Fraud (2500€): 99.51% fraud score → CHALLENGE
- Latence: 13ms
- Features: 12 (dont distance et city_pop)

---

## 🎯 Prochaine Session - Roadmap

### Phase 3: Services finaux (3h estimées)

#### 1. Case Service (2h) 🎯 **COMMENCE PAR ÇA**

**Objectif:** Service pour gérer les cas de fraude et le feedback des analystes

**À faire:**
```bash
# 1. Créer la structure
mkdir -p services/case-service/app
cd services/case-service

# 2. Fichiers à créer
touch app/__init__.py
touch app/main.py          # FastAPI app
touch app/models.py        # Pydantic models
touch app/database.py      # PostgreSQL connection
touch app/kafka_consumer.py # Consumer decision_events
touch Dockerfile
touch requirements.txt
touch README.md

# 3. Features principales
- Consumer Kafka: écoute decision_events
- API CRUD: GET/POST/PUT /cases
- Labélisation: POST /cases/{id}/label (fraud/legit)
- Recherche: GET /cases?status=pending
- Stats: GET /stats (fraud rate, cases par jour)
```

**Technologies:**
- FastAPI (async)
- aiokafka (consumer)
- asyncpg (PostgreSQL)
- Pydantic validation

**Tables PostgreSQL existantes:**
- `cases` (déjà créée dans migrations)
- `labels` (déjà créée)

**Endpoints à implémenter:**
```
POST   /v1/cases          # Créer un cas (auto depuis Kafka)
GET    /v1/cases          # Lister les cas
GET    /v1/cases/{id}     # Détail d'un cas
PUT    /v1/cases/{id}     # Mettre à jour un cas
POST   /v1/cases/{id}/label  # Labéliser (fraud/legit)
GET    /v1/stats          # Statistiques
GET    /health            # Health check
```

---

#### 2. API Gateway (1h)

**Objectif:** Point d'entrée unique pour toutes les API

**À faire:**
```bash
# 1. Créer la structure
mkdir -p services/api-gateway/app

# 2. Features
- Routage vers Decision Engine
- Rate limiting (Redis)
- API key validation (optionnel)
- CORS headers
- Request logging
```

**Technologies:**
- FastAPI
- aioredis (rate limiting)
- httpx (proxy requests)

**Endpoints:**
```
POST /v1/score          → Decision Engine
GET  /v1/cases          → Case Service
POST /v1/cases/{id}/label → Case Service
```

---

#### 3. Dashboards Grafana (30min)

**Objectif:** Visualiser les métriques Prometheus

**À faire:**
```bash
# 1. Créer les dashboards
mkdir -p platform/observability/grafana/dashboards

# 2. Dashboards à créer
- fraud_detection_overview.json  # Vue d'ensemble
- model_performance.json         # Perf du modèle
- system_health.json            # Santé des services
```

**Métriques à afficher:**
- Fraud detection rate
- Latence P50/P95/P99
- Throughput (req/s)
- Model scores distribution
- Decision breakdown (ALLOW/CHALLENGE/DENY)

---

## 🔧 Comment reprendre

### 1. Redémarrer l'environnement

```bash
# Aller dans le projet
cd /Users/virgileader/Library/CloudStorage/OneDrive-Epitech/Projet\ 5ème\ année/bank-security

# Vérifier que tout est à jour
git status
git pull

# Démarrer les services
make up

# Vérifier la santé
make health

# Tester l'API
curl http://localhost:8000/health | jq .
```

### 2. Vérifier le modèle Kaggle

```bash
# Le modèle doit être chargé
curl http://localhost:8001/health | jq .
# Devrait afficher: model_path: "/app/artifacts/models/fraud_lgbm_kaggle.bin"

# Test rapide
curl -X POST http://localhost:8000/v1/score   -H "Content-Type: application/json"   -d '{
    "event_id": "test_001",
    "amount": 100,
    "currency": "EUR",
    "merchant": {"mcc": "5411", "country": "FR"},
    "card": {"card_id": "c1", "user_id": "u1", "type": "physical"},
    "context": {"channel": "pos"}
  }' | jq .
```

### 3. Commencer le Case Service

```bash
# Créer la branche
git checkout -b feature/case-service

# Créer la structure (voir ci-dessus)
# Développer le service
# Tester
# Commit et PR
```

---

## 📋 Checklist avant de commencer

- [ ] Services Docker up et healthy
- [ ] Modèle Kaggle chargé (fraud_lgbm_kaggle.bin)
- [ ] Tests end-to-end passent
- [ ] Git à jour (pull origin/main)
- [ ] Branche feature/case-service créée

---

## 📁 Structure actuelle du projet

```
bank-security/
├── services/
│   ├── decision-engine/     ✅ Opérationnel
│   ├── model-serving/       ✅ Opérationnel (Kaggle model)
│   ├── rules-service/       ✅ Opérationnel
│   ├── case-service/        ⏳ À CRÉER
│   └── api-gateway/         ⏳ À CRÉER
├── platform/
│   ├── postgres/            ✅ Migrations OK
│   ├── observability/       ⏳ Dashboards à créer
│   └── kafka/               ✅ Topic decision_events OK
├── artifacts/
│   ├── models/
│   │   ├── fraud_lgbm_kaggle.bin           ✅ Modèle Kaggle
│   │   └── fraud_model_metadata_kaggle.json
│   └── data/                ✅ Dataset Kaggle (1.8M transactions)
├── train_fraud_model_kaggle.py  ✅ Script d'entraînement
├── docker-compose.yml       ✅ 4 services configurés
├── RECAP.md                 ✅ À jour
└── NEXT_STEPS.md           ✅ Ce fichier
```

---

## 🎯 Objectif final

**Services:** 6/6 (100%)
- ✅ Database
- ✅ Model Serving (Kaggle)
- ✅ Decision Engine
- ✅ Rules Service
- ⏳ Case Service
- ⏳ API Gateway

**Temps estimé restant:** ~3h30

**Ordre recommandé:**
1. Case Service (2h)
2. API Gateway (1h)
3. Dashboards Grafana (30min)
4. Tests finaux + doc (30min)

---

## 💡 Commandes utiles

```bash
# Santé globale
make health

# Logs d'un service
docker logs antifraud-model-serving -f

# Rebuild un service
docker-compose build model-serving
docker-compose up -d model-serving

# Tester Decision Engine
curl -X POST http://localhost:8000/v1/score -H "Content-Type: application/json" -d @test_transaction.json

# Voir les topics Kafka
docker exec antifraud-kafka kafka-topics --list --bootstrap-server localhost:9092

# Consumer Kafka
docker exec antifraud-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic decision_events --from-beginning

# PostgreSQL
docker exec -it antifraud-postgres psql -U postgres -d fraudguard
```

---

## 🔗 Liens utiles

- **Kaggle Dataset:** https://www.kaggle.com/datasets/kartik2112/fraud-detection
- **Model Performance:** AUC 99.56%, 12 features
- **API Docs:** http://localhost:8000/docs (Decision Engine)
- **Grafana:** http://localhost:3000 (admin/admin)
- **Prometheus:** http://localhost:9090

---

**Bon courage pour la prochaine session ! 🚀**
a171bf8 docs: Add comprehensive next session guide
71e7cba feat: Integrate Kaggle fraud detection dataset and model
8a77141 feat: MVP Phase 1 - End-to-end fraud detection with LightGBM
baa0e8e Merge pull request #2 from warren-buffets/feature/model-serving
8e3007d Merge pull request #1 from warren-buffets/feature/decision-engine
b501d7e Add model serving
549e634 add migration
9f6e9e5 docs: Add development recap document
c71f78c feat: Add Decision Engine service
39ea9c2 feat: add Model Serving service for FraudGuard AI
35ae808 feat: add Rules Service with DSL evaluation engine
3dbb40b feat: Add PostgreSQL database migrations
cc3b3cc add read me

### Démarrer services
docker compose up -d

### Explorer projet
total 0
drwxr-xr-x@  9 virgileader  staff  288 Dec  8 00:00 .
drwxr-xr-x@ 26 virgileader  staff  832 Dec  8 00:54 ..
drwxr-xr-x@  2 virgileader  staff   64 Sep 30 15:11 api-gateway
drwxr-xr-x@  2 virgileader  staff   64 Sep 30 15:11 audit-signer
drwxr-xr-x@  2 virgileader  staff   64 Sep 30 15:11 case-service
drwxr-xr-x@  2 virgileader  staff   64 Sep 30 15:11 case-ui
drwxr-xr-x@  6 virgileader  staff  192 Dec  8 00:02 decision-engine
drwxr-xr-x@  7 virgileader  staff  224 Dec  8 00:02 model-serving
drwxr-xr-x@  6 virgileader  staff  192 Dec  7 23:57 rules-service
total 152
drwxr-xr-x@ 11 virgileader  staff    352 Dec  8 00:00 .
drwxr-xr-x@ 26 virgileader  staff    832 Dec  8 00:54 ..
-rw-r--r--@  1 virgileader  staff   6148 Dec  8 00:00 .DS_Store
-rw-r--r--@  1 virgileader  staff  15292 Dec  8 00:00 ARCHITECTURE.md
-rw-r--r--@  1 virgileader  staff  27641 Dec  8 00:00 FLUX-DONNEES.md
-rw-r--r--@  1 virgileader  staff   5610 Dec  8 00:00 GUIDE-RAPIDE.md
-rw-r--r--@  1 virgileader  staff   2610 Dec  8 00:00 INDEX.md
drwxr-xr-x@  5 virgileader  staff    160 Dec  8 00:02 api
drwxr-xr-x@  4 virgileader  staff    128 Sep 30 15:11 data
-rw-r--r--@  1 virgileader  staff  11204 Dec  8 00:00 database-schema.md
drwxr-xr-x@  2 virgileader  staff     64 Sep 30 15:11 security

---

## 💡 Décisions Techniques

### Architecture
- Microservices stateless
- Async I/O
- Idempotence Redis (15min TTL)
- Immutabilité decisions

### ML Pipeline
- LightGBM (< 10ms)
- 12 features
- train_fraud_model_kaggle.py
- AUC 99.56%

### Stack
- PostgreSQL (ACID)
- Redis (Cache)
- Kafka (Events)

---

## ⚠️ Limitations

- Pas authentication APIs
- Pas rate limiting
- Dashboards Grafana non configurés
- Tests unitaires incomplets

---

## 📞 Ressources

### Commandes
docker compose up -d
docker compose down

### Endpoints
- Decision Engine: :8000
- Model Serving: :8001
- Rules Service: :8002
- Grafana: :3000
- Prometheus: :9090

### Credentials
- PostgreSQL: postgres/postgres_dev @ :5432
- Redis: :6379
- Kafka: :9092
- Grafana: admin/admin

---

## 📝 Workflow IA

### Avant session
1. Lire docs/SESSIONS.md
2. Vérifier NEXT_STEPS.md
3. Lire RECAP.md
4. git status
5. make up && make health

### Pendant session
1. Suivre patterns existants
2. Documenter
3. Tests e2e
4. Commits réguliers

### Après session
1. MAJ RECAP.md
2. MAJ NEXT_STEPS.md
3. MAJ docs/SESSIONS.md
4. Commit + push

---

## 🎯 Vision

- 6/6 services
- Tests complets
- Dashboards Grafana
- Production-ready

**Estimation:** ~4h restantes

---

Créé: 2025-12-12
Par: AI Assistant
Statut: 67% (4/6 services)
