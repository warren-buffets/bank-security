# Guide de Configuration de l'Environnement - FraudGuard AI

## 🐍 Environnement Python

### Créer l'environnement virtuel

```bash
# Créer l'environnement (déjà fait)
python3 -m venv venv
```

### Activer l'environnement

```bash
# Sur macOS/Linux
source venv/bin/activate

# Sur Windows
venv\Scripts\activate
```

### Installer les dépendances de tous les services

```bash
# Une fois l'environnement activé
pip install --upgrade pip

# Installer les dépendances de chaque service
pip install -r services/model-serving/requirements.txt
pip install -r services/decision-engine/requirements.txt
pip install -r services/rules-service/requirements.txt
```

### Désactiver l'environnement

```bash
deactivate
```

---

## 🐳 Docker (Recommandé pour production)

### Installer Docker Desktop

**macOS:**
```bash
brew install --cask docker
```

Ou télécharger depuis: https://www.docker.com/products/docker-desktop

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Vérifier l'installation

```bash
docker --version
docker-compose --version
```

---

## 📦 Services requis

### Option 1: Avec Docker (Recommandé)

Tout est déjà configuré dans `docker-compose.yml`:

```bash
# Démarrer tous les services
make up

# Vérifier la santé
make health
```

### Option 2: Installation manuelle

Si vous n'utilisez pas Docker, installez:

**PostgreSQL:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Redis:**
```bash
brew install redis
brew services start redis
```

**Kafka:**
```bash
brew install kafka
brew services start zookeeper
brew services start kafka
```

---

## 🧪 Tester un service individuellement

### Exemple: Model Serving

```bash
# Activer l'environnement
source venv/bin/activate

# Aller dans le service
cd services/model-serving

# Lancer le service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Dans un autre terminal, tester
curl http://localhost:8001/health
```

### Exemple: Decision Engine

```bash
source venv/bin/activate
cd services/decision-engine

# Variables d'environnement nécessaires
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=antifraud
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres_dev
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Lancer
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔧 Configuration des variables d'environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos valeurs
nano .env  # ou votre éditeur préféré
```

Variables principales:
- `POSTGRES_*` - Configuration PostgreSQL
- `REDIS_*` - Configuration Redis
- `KAFKA_*` - Configuration Kafka
- `MODEL_SERVING_*` - Configuration ML
- `DECISION_ENGINE_*` - Configuration orchestrateur

---

## 📝 Structure recommandée

```
venv/                    # Environnement virtuel Python (gitignored)
.env                     # Variables d'environnement (gitignored)
services/
  ├── model-serving/
  ├── decision-engine/
  └── rules-service/
```

---

## 🚀 Workflow de développement

### 1. Première installation

```bash
# Créer et activer l'environnement
python3 -m venv venv
source venv/bin/activate

# Installer toutes les dépendances
pip install -r services/model-serving/requirements.txt
pip install -r services/decision-engine/requirements.txt
pip install -r services/rules-service/requirements.txt

# Configuration
cp .env.example .env
```

### 2. Développement quotidien

```bash
# Activer l'environnement
source venv/bin/activate

# Travailler sur un service
cd services/model-serving
uvicorn app.main:app --reload

# Quand terminé
deactivate
```

### 3. Tests complets

```bash
# Avec Docker (recommandé)
make up
make health
make test

# Sans Docker (manuel)
source venv/bin/activate
# Lancer chaque service dans un terminal séparé
```

---

## 🎓 Commandes utiles

```bash
# Lister les packages installés
pip list

# Vérifier l'environnement actif
which python

# Mettre à jour un package
pip install --upgrade [package]

# Freezer les dépendances
pip freeze > requirements.txt

# Nettoyer l'environnement
deactivate
rm -rf venv
```

---

## ⚠️ Dépannage

### Python introuvable
```bash
# Installer Python 3.11+
brew install python@3.11
```

### Permission denied
```bash
chmod +x venv/bin/activate
```

### Module not found
```bash
# Vérifier que l'environnement est activé
which python  # Doit pointer vers venv/bin/python

# Réinstaller les dépendances
pip install -r requirements.txt
```

### Port déjà utilisé
```bash
# Trouver le processus
lsof -i :8000

# Tuer le processus
kill -9 [PID]
```

---

**Environnement créé le**: 2025-12-05
**Python requis**: 3.11+
**Docker recommandé**: Oui (pour faciliter le déploiement)
