# Status de Configuration - FraudGuard

## Date: 2026-01-19

## Etapes Complétées ✅

### 1. Structure du Projet
- Projet cloné et structure vérifiée
- Répertoire: `c:\Users\fpvmo\OneDrive - Epitech\Projet 5ème année\bank-security`
- Branche: `main`

### 2. Fichiers de Configuration
- Fichiers `-PC-Warren` remplacés par leurs versions opérationnelles
- Fichiers mis à jour:
  - `.env` (configuration environnement)
  - `docker-compose.yml`
  - `Makefile`
  - `README.md`
  - Tous les services (decision-engine, model-serving, rules-service)
  - Migrations PostgreSQL
  - Documentation complète

### 3. Données Kaggle
- ✅ `fraudTrain.csv` (335 MB) - présent dans `artifacts/data/`
- ✅ `fraudTest.csv` (144 MB) - présent dans `artifacts/data/`

### 4. Dépendances Python
- Python 3.13.5 installé
- Bibliothèques installées:
  - numpy 2.3.1
  - pandas 2.3.0
  - scikit-learn 1.8.0
  - lightgbm 4.6.0
  - fastapi 0.128.0
  - uvicorn 0.40.0
  - pydantic 2.12.5
  - redis 7.1.0
  - httpx 0.28.1
  - pytest 9.0.2
  - pytest-asyncio 1.3.0
  - prometheus-client 0.24.1

## Etapes Restantes ⏳

### 5. Installation Docker Desktop
**Status**: ❌ NON INSTALLÉ

Docker n'est pas détecté sur ce PC. C'est REQUIS pour exécuter les services.

**Actions à faire**:
1. Télécharger Docker Desktop pour Windows: https://www.docker.com/products/docker-desktop/
2. Installer Docker Desktop
3. Redémarrer l'ordinateur si nécessaire
4. Vérifier l'installation: `docker --version`
5. S'assurer que Docker Desktop est lancé (icône dans la barre des tâches)

### 6. Démarrage des Services Docker
Une fois Docker installé, exécuter:
```bash
cd "c:\Users\fpvmo\OneDrive - Epitech\Projet 5ème année\bank-security"
docker compose up -d
```

### 7. Vérification de la Santé des Services
Tester les endpoints:
```bash
# Decision Engine
curl http://localhost:8000/health

# Model Serving
curl http://localhost:8001/health

# Rules Service
curl http://localhost:8002/health
```

## Ports des Services

| Service | Port |
|---------|------|
| decision-engine | 8000 |
| model-serving | 8001 |
| rules-service | 8002 |
| case-service | 8003 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Kafka | 9092 |
| Prometheus | 9090 |
| Grafana | 3000 |

## Prochaines Actions

1. **INSTALLER DOCKER DESKTOP** (priorité haute)
2. Démarrer les services avec `docker compose up -d`
3. Vérifier que tous les services sont sains
4. Optionnel: Entraîner le modèle ML avec `python scripts/train_fraud_model_kaggle.py`

## Notes

- Environnement virtuel Python: `venv/` (existe déjà)
- Fichiers temporaires `-PC-Warren` conservés pour référence
- Configuration `.env` prête pour le développement local
- Toutes les migrations de base de données sont prêtes

## Commandes Utiles

```bash
# Activer l'environnement virtuel (si nécessaire)
source venv/Scripts/activate  # Git Bash
# ou
venv\Scripts\activate.bat  # CMD

# Voir les logs d'un service
docker compose logs -f decision-engine

# Arrêter tous les services
docker compose down

# Rebuild un service
docker compose up -d --build decision-engine

# Appliquer les migrations DB
./scripts/db-helper.sh migrate
```
