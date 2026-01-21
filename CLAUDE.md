# FraudGuard - Instructions pour Claude

## Projet
Plateforme de détection de fraude bancaire en temps réel avec architecture microservices.

## Stack Technique
- **Backend**: Python 3.10+, FastAPI
- **ML**: LightGBM, scikit-learn
- **Infra**: Docker, Kubernetes, Kafka, Redis, PostgreSQL
- **Observability**: Prometheus, Grafana

## Structure du Projet
```
bank-security/
├── services/
│   ├── decision-engine/     # Orchestrateur principal
│   ├── model-serving/       # Service ML (LightGBM)
│   ├── rules-service/       # Moteur de règles
│   └── case-service/        # Gestion des cas de fraude
├── platform/
│   ├── kafka/               # Config Kafka
│   ├── postgres/            # Migrations DB
│   └── observability/       # Prometheus + Grafana
├── deploy/
│   ├── k8s-manifests/       # Déploiement Kubernetes
│   └── helm/                # Chart Helm
├── scripts/                 # Helper scripts
├── tests/                   # Tests (unit, integration, e2e)
├── artifacts/
│   ├── models/              # Modèles ML
│   └── data/                # Données (non versionnées)
└── docs/                    # Documentation
```

## Commandes Essentielles

### Démarrage Local
```bash
# Démarrer tous les services
docker-compose up -d

# Avec override pour dev
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Logs d'un service
docker-compose logs -f decision-engine
```

### Tests
```bash
# Tous les tests
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Avec couverture
pytest --cov=services --cov-report=html
```

### Base de données
```bash
# Appliquer les migrations
./scripts/db-helper.sh migrate

# Reset DB
./scripts/db-helper.sh reset
```

### ML Model
```bash
# Entraîner le modèle
python scripts/train_fraud_model_kaggle.py

# Le modèle est sauvegardé dans artifacts/models/
```

---

# SETUP NOUVEAU PC - ETAPES A SUIVRE

## Etape 1: Cloner et installer
```bash
git clone https://github.com/warren-buffets/bank-security.git
cd bank-security
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements-dev.txt
```

## Etape 2: Télécharger les données Kaggle
Les fichiers CSV sont trop volumineux pour GitHub. Télécharge-les depuis Kaggle:

1. Va sur https://www.kaggle.com/datasets/kartik2112/fraud-detection
2. Télécharge `fraudTrain.csv` et `fraudTest.csv`
3. Place-les dans `artifacts/data/`

Ou via CLI Kaggle:
```bash
pip install kaggle
kaggle datasets download -d kartik2112/fraud-detection -p artifacts/data/ --unzip
```

## Etape 3: Configurer l'environnement
```bash
cp .env.example .env
# Editer .env avec tes valeurs si nécessaire
```

## Etape 4: Démarrer Docker
```bash
docker-compose up -d
```

## Etape 5: Appliquer les migrations DB
```bash
# Appliquer toutes les migrations
for f in platform/postgres/migrations/V*.sql; do
  docker exec -i antifraud-postgres psql -U postgres -d antifraud < "$f"
done

# Ou migration par migration
docker exec -i antifraud-postgres psql -U postgres -d antifraud < platform/postgres/migrations/V001__init.sql
docker exec -i antifraud-postgres psql -U postgres -d antifraud < platform/postgres/migrations/V002__indices.sql
docker exec -i antifraud-postgres psql -U postgres -d antifraud < platform/postgres/migrations/V003__triggers.sql
docker exec -i antifraud-postgres psql -U postgres -d antifraud < platform/postgres/migrations/V004__seed_data.sql
docker exec -i antifraud-postgres psql -U postgres -d antifraud < platform/postgres/migrations/V005__rules_service_compat.sql
```

## Etape 6: Vérifier que tout fonctionne
```bash
# Santé des services
curl http://localhost:8000/health  # decision-engine
curl http://localhost:8001/health  # model-serving
curl http://localhost:8003/health  # rules-service
curl http://localhost:8002/health  # case-service

# Vérifier que les règles sont chargées (doit retourner 11 règles)
curl http://localhost:8003/rules

# Test de prédiction complet
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-123",
    "amount": 500.0,
    "currency": "EUR",
    "merchant": {"id": "m1", "name": "Store", "mcc": "5411", "country": "FR"},
    "card": {"card_id": "c1", "user_id": "u1", "type": "physical"},
    "context": {"ip": "1.2.3.4", "channel": "web"}
  }'
```

## Etape 7: Nettoyer les fichiers temporaires locaux
Il peut rester des fichiers `-PC-Warren` à supprimer:
```bash
find . -name "*-PC-Warren*" -type f -delete
```

---

# Ports des Services
| Service | Port |
|---------|------|
| decision-engine | 8000 |
| model-serving | 8001 |
| case-service | 8002 |
| rules-service | 8003 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Kafka | 9092 |
| Prometheus | 9090 |
| Grafana | 3000 |

---

# Conventions de Code
- Style: PEP 8, Black formatter
- Types: Utiliser type hints
- Tests: pytest, mocks pour services externes
- Commits: Conventional commits (feat:, fix:, docs:, etc.)

---

# Prochaines Etapes Suggérées
1. Implémenter les tests E2E manquants
2. Ajouter l'authentification JWT
3. Dashboard Grafana pour les métriques ML
4. Alerting avec AlertManager
5. Documentation API OpenAPI complète
