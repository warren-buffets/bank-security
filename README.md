# SafeGuard - Détection de Fraude Bancaire Temps Réel

> **Protégez chaque transaction. En un clin d'oeil.**

---

## En Bref

**SafeGuard** est un moteur de détection de fraude temps réel pour paiements par carte bancaire. Il analyse chaque transaction en **moins de 100ms** et décide :

| Décision | Condition | Action |
|----------|-----------|--------|
| **ALLOW** | Score < 0.50 | Transaction autorisée |
| **CHALLENGE** | Score 0.50-0.70 | Demande 2FA |
| **DENY** | Score > 0.70 | Transaction bloquée |

### Chiffres Clés

| Métrique | Valeur |
|----------|--------|
| Latence P95 | < 100ms |
| Détection (Recall) | 82% |
| Faux Positifs (FPR) | < 5% |
| AUC Modèle | 0.823 |

---

## Démarrage Rapide

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Dataset IEEE-CIS (optionnel pour training)

### Installation

```bash
# 1. Cloner le repo
git clone <repo-url>
cd bank-security

# 2. Configurer l'environnement
cp .env.example .env

# 3. Démarrer les services
docker-compose up -d

# 4. Appliquer les migrations
for f in platform/postgres/migrations/V*.sql; do
  docker exec -i safeguard-postgres psql -U postgres -d safeguard < "$f"
done

# 5. Vérifier la santé
curl http://localhost:8000/health
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Decision Engine | 8000 | Orchestrateur principal |
| Model Serving | 8001 | Inférence ML (LightGBM) |
| Rules Service | 8003 | Moteur de règles |
| Case Service | 8002 | Gestion des cas |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Cache & idempotence |
| Kafka | 9092 | Event streaming |
| Prometheus | 9090 | Métriques |
| Grafana | 3000 | Dashboards |

---

## Tester l'API

```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-001",
    "amount": 250.0,
    "currency": "EUR",
    "merchant": {
      "id": "m1",
      "name": "Carrefour Paris",
      "mcc": "5411",
      "country": "FR"
    },
    "card": {
      "card_id": "c1",
      "user_id": "u1",
      "type": "physical"
    },
    "context": {
      "ip": "82.64.1.1",
      "channel": "pos"
    }
  }'
```

**Réponse** :
```json
{
  "event_id": "test-001",
  "decision_id": "dec_abc123",
  "decision": "CHALLENGE",
  "score": 0.65,
  "reasons": ["Medium risk score: 0.65"],
  "rule_hits": [],
  "latency_ms": 47,
  "model_version": "v1.0.0",
  "requires_2fa": true
}
```

---

## Architecture

```
                    ┌─────────────────┐
                    │  Decision Engine │ (Port 8000)
                    │   Orchestrator   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │  Model   │   │  Rules   │   │   Case   │
       │ Serving  │   │ Service  │   │ Service  │
       │ (8001)   │   │ (8003)   │   │ (8002)   │
       └────┬─────┘   └──────────┘   └──────────┘
            │
            ▼
    ┌───────────────┐
    │  ip-api.com   │ (Géolocalisation IP)
    │  + Redis Cache│
    └───────────────┘
```

### Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, FastAPI |
| ML | LightGBM (IEEE-CIS dataset) |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Messaging | Apache Kafka |
| Monitoring | Prometheus + Grafana |

---

## Modèle ML (v3)

### Dataset : IEEE-CIS Fraud Detection

| Caractéristique | Valeur |
|-----------------|--------|
| Source | Vesta Corporation (données réelles) |
| Transactions | 590,540 |
| Taux de fraude | 3.5% |
| Features | 12 |

### Performance

| Métrique | Valeur |
|----------|--------|
| AUC-ROC | 0.823 |
| Recall | 82% |
| Precision | 20% |

### Features

1. `amount` - Montant de la transaction
2. `trans_hour` - Heure de la transaction
3. `trans_day` - Jour de la semaine
4. `merchant_mcc` - Code catégorie marchand
5. `card_type` - Type de carte (0=physique, 1=virtuelle)
6. `channel` - Canal (0=app, 1=web, 2=pos, 3=atm)
7. `is_international` - Transaction internationale
8. `is_night` - Heure nocturne (23h-5h)
9. `is_weekend` - Week-end
10. `amount_category` - Catégorie de montant
11. `distance_category` - Distance IP ↔ marchand
12. `city_pop` - Population de la ville (géoloc IP)

---


## 🛡️ Générateur de fraudes – Intégration des features

Le générateur de fraudes synthétiques produit des transactions complètes en instanciant chaque feature de manière **cohérente, contrôlée et scénarisée**, afin de simuler des comportements réels (légitimes et frauduleux) sans utiliser de données réelles.

### 🔁 Rôle du générateur
- **Simuler** des transactions bancaires réalistes pour l’entraînement ML
- **Injecter** des patterns de fraude contrôlés (card testing, ATO, phishing, etc.)
- **Tester** le Decision Engine SafeGuard en conditions proches du réel
- **Équilibrer** distributions, corrélations et biais statistiques

---

### ⚙️ Génération des features
Chaque transaction est générée selon 3 couches :

#### 1. **Base transactionnelle (réalisme)**
- `amount`, `amount_category`
- `trans_hour`, `trans_day`, `is_night`, `is_weekend`
- `merchant_mcc`, `channel`, `card_type`

→ Assure une distribution proche du trafic réel.

#### 2. **Contexte géographique et comportemental**
- `is_international`
- `distance_category`
- `city_pop`

→ Simule le déplacement, l’anomalie géographique et le risque contextuel.

#### 3. **Injection de scénarios de fraude**
Selon le scénario, certaines features sont **forcées ou corrélées** :

| Scénario | Features impactées |
|---------|--------------------|
| card_testing | petits `amount`, répétitions, `channel=web`, `is_night=1` |
| account_takeover | nouveau device, `distance_category=far`, `is_international=1` |
| phishing | horaires atypiques, MCC risqués |
| money_laundering | montants structurés, répétition, MCC spécifiques |
| merchant_fraud | MCC ciblé, `channel=pos` |
| chargeback_fraud | délai, montants moyens, e-commerce |

---

### ✅ Validation post-génération
- **Contrôler** la cohérence feature ↔ scénario
- **Dédupliquer** les transactions
- **Vérifier** les distributions (pas de fuite de patterns)
- **Garantir** la séparabilité fraude / légitime sans sur-apprentissage

---

### 🚀 Sortie
Les features générées alimentent directement :
- les modèles de détection de fraude,
- les pipelines d’entraînement et de tests,
- le Decision Engine SafeGuard (ALLOW / CHALLENGE / DENY),
- les analyses de performance et de robustesse.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/INDEX.md](docs/INDEX.md) | Index de la documentation |
| [docs/SIX_PAGER.md](docs/SIX_PAGER.md) | Six-Pager technique (soutenance) |
| [docs/SIX_PAGER_ML_MODEL.md](docs/SIX_PAGER_ML_MODEL.md) | Modèle ML v3 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique |
| [docs/FLUX-DONNEES.md](docs/FLUX-DONNEES.md) | Flux de données |
| [docs/GUIDE-RAPIDE.md](docs/GUIDE-RAPIDE.md) | Guide de démarrage |
| [docs/api/openapi.yaml](docs/api/openapi.yaml) | Spécification API |

---

## Structure du Projet

```
bank-security/
├── services/
│   ├── decision-engine/     # Orchestrateur (Port 8000)
│   ├── model-serving/       # Inférence ML (Port 8001)
│   ├── rules-service/       # Règles métier (Port 8003)
│   └── case-service/        # Gestion cas (Port 8002)
├── platform/
│   ├── postgres/migrations/ # Migrations SQL
│   └── observability/       # Prometheus, Grafana
├── artifacts/
│   ├── models/              # Modèles ML (.bin)
│   └── data/                # Datasets (non versionnés)
├── scripts/                 # Scripts helper
├── docs/                    # Documentation
├── deploy/                  # K8s & Helm
└── tests/                   # Tests
```

---

## Commandes Utiles

```bash
# Services
docker-compose up -d          # Démarrer
docker-compose down           # Arrêter
docker-compose logs -f        # Logs

# Base de données
./scripts/db-helper.sh migrate
./scripts/db-helper.sh stats

# ML
python scripts/train_fraud_model_ieee.py

# Tests
pytest tests/
```

---

## Roadmap

### Fait
- [x] Architecture microservices
- [x] Modèle ML v3 (IEEE-CIS)
- [x] Géolocalisation IP (ip-api.com + cache Redis)
- [x] Métriques Prometheus
- [x] Documentation complète

### À Faire
- [ ] Interface Case UI (analystes)
- [ ] Authentification JWT
- [ ] Dashboard Grafana ML
- [ ] Tests E2E
- [ ] Déploiement Kubernetes

---

## Équipe

**Warren Buffets** - Projet 5ème année Epitech

Contact : virgile.ader@epitech.digital

---

**SafeGuard** - Détection de fraude bancaire temps réel

