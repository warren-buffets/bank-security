# SafeGuard - Instructions pour Claude

## Projet
**SafeGuard** - Plateforme de détection de fraude bancaire en temps réel avec architecture microservices.

## Stack Technique
- **Backend**: Python 3.11+, FastAPI
- **ML**: LightGBM (dataset IEEE-CIS)
- **Infra**: Docker, Kubernetes, Kafka, Redis, PostgreSQL
- **Observability**: Prometheus, Grafana

## Structure du Projet
```
bank-security/
├── services/
│   ├── decision-engine/     # Orchestrateur (Port 8000)
│   ├── model-serving/       # ML LightGBM (Port 8001)
│   ├── rules-service/       # Règles métier (Port 8003)
│   └── case-service/        # Gestion cas (Port 8002)
├── platform/
│   ├── postgres/migrations/ # Migrations SQL
│   └── observability/       # Prometheus + Grafana
├── artifacts/
│   ├── models/              # Modèles ML (.bin)
│   └── data/                # Datasets (non versionnés)
├── scripts/                 # Scripts helper
├── docs/                    # Documentation
├── deploy/                  # K8s & Helm
└── tests/                   # Tests
```

## Commandes Essentielles

### Démarrage Local
```bash
docker-compose up -d
docker-compose logs -f decision-engine
```

### Tests
```bash
pytest
pytest --cov=services
```

### Base de données
```bash
./scripts/db-helper.sh migrate
./scripts/db-helper.sh reset
```

### ML Model
```bash
# Entraîner avec IEEE-CIS (recommandé)
python scripts/train_fraud_model_ieee.py

# Modèle sauvegardé dans artifacts/models/
```

---

# SETUP NOUVEAU PC

## 1. Cloner et installer
```bash
git clone https://github.com/warren-buffets/bank-security.git
cd bank-security
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## 2. Télécharger le dataset IEEE-CIS
```bash
pip install kaggle
kaggle competitions download -c ieee-fraud-detection -p artifacts/data/ --unzip
```

## 3. Configurer l'environnement
```bash
cp .env.example .env
```

## 4. Démarrer Docker
```bash
docker-compose up -d
```

## 5. Appliquer les migrations
```bash
for f in platform/postgres/migrations/V*.sql; do
  docker exec -i safeguard-postgres psql -U postgres -d safeguard < "$f"
done
```

## 6. Vérifier
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8003/health
```

## 7. Tester l'API
```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-123",
    "amount": 250.0,
    "currency": "EUR",
    "merchant": {"id": "m1", "name": "Store", "mcc": "5411", "country": "FR"},
    "card": {"card_id": "c1", "user_id": "u1", "type": "physical"},
    "context": {"ip": "82.64.1.1", "channel": "pos"}
  }'
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

# Modèle ML (v3)

**Dataset**: IEEE-CIS Fraud Detection (Vesta Corporation)
- 590K transactions réelles
- Taux de fraude: 3.5%
- AUC: 0.823

**Features (12)**:
1. amount, trans_hour, trans_day
2. merchant_mcc, card_type, channel
3. is_international, is_night, is_weekend
4. amount_category, distance_category, city_pop

**Géolocalisation IP**: ip-api.com avec cache Redis (TTL 24h)

---

# Documentation

| Document | Description |
|----------|-------------|
| [docs/INDEX.md](docs/INDEX.md) | Index documentation |
| [docs/SIX_PAGER.md](docs/SIX_PAGER.md) | Six-Pager (soutenance) |
| [docs/SIX_PAGER_ML_MODEL.md](docs/SIX_PAGER_ML_MODEL.md) | Modèle ML v3 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture |

---

# Conventions
- Style: PEP 8, Black
- Types: Type hints obligatoires
- Tests: pytest
- Commits: Conventional commits

---

# Roadmap

### Fait
- [x] Architecture microservices
- [x] Modèle ML v3 (IEEE-CIS)
- [x] Géolocalisation IP
- [x] Documentation complète

### À Faire
- [ ] Tests E2E
- [ ] Authentification JWT
- [ ] Dashboard Grafana ML
- [ ] Déploiement K8s
