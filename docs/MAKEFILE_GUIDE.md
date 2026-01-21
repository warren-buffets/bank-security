# Guide du Makefile - FraudGuard

## Introduction

Le [Makefile](../Makefile) est l'**interface principale** pour interagir avec le projet FraudGuard. Il simplifie l'utilisation des scripts shell et fournit des commandes courtes et mémorables.

## Philosophie : Make vs Scripts Shell

### Quand utiliser `make` ?
✅ **Commandes fréquentes** : `make up`, `make logs`, `make test`
✅ **Workflows complets** : `make setup` (démarre tout + migrations + health check)
✅ **Interface simple** : Vous tapez juste `make` pour voir toutes les options

### Quand utiliser les scripts shell directement ?
✅ **Opérations avancées** : `./scripts/kafka-helper.sh create my-topic 10`
✅ **Arguments personnalisés** : `./scripts/db-helper.sh query "SELECT * FROM ..."`
✅ **Options spécifiques** : `./scripts/ml-helper.sh train --epochs 100`

**En résumé** : `make` = raccourcis pour 80% des cas d'usage, scripts = puissance complète pour les 20% restants.

---

## Commandes Essentielles

### Voir toutes les commandes disponibles
```bash
make
# ou
make help
```

---

## Catégories de Commandes

### 1. 🐳 Docker Commands

#### Démarrer tous les services
```bash
make up
```
Lance tous les conteneurs en arrière-plan (Postgres, Redis, Kafka, services Python).

#### Arrêter tous les services
```bash
make down
```

#### Redémarrer
```bash
make restart
```
Équivalent à `make down && make up`.

#### Voir les logs
```bash
# Tous les services
make logs

# Service spécifique
make logs-decision     # decision-engine
make logs-model        # model-serving
make logs-rules        # rules-service
make logs-case         # case-service
```

#### Statut des conteneurs
```bash
make ps
```

#### Rebuild après modifications de code
```bash
make rebuild
```

#### Nettoyer complètement
```bash
make clean
```
⚠️ **Attention** : Supprime volumes, conteneurs et images inutilisées.

---

### 2. 🗄️ Database Commands

#### Appliquer les migrations
```bash
make db-migrate
```
Applique tous les fichiers SQL dans [platform/postgres/migrations/](../platform/postgres/migrations/).

#### Reset complet de la base
```bash
make db-reset
```
⚠️ **Attention** : DROP toutes les tables puis re-applique les migrations.

#### Statistiques de la base
```bash
make db-stats
```
Affiche la taille des tables, nombre de lignes, etc.

#### Se connecter à psql
```bash
make db-connect
```
Lance un shell PostgreSQL interactif.

---

### 3. 📨 Kafka Commands

#### Lister tous les topics
```bash
make kafka-list
```

#### Consommer les événements de fraude en temps réel
```bash
make kafka-consume
```
Écoute le topic `fraud-events` et affiche les messages.

---

### 4. 🔴 Redis Commands

#### Informations du serveur Redis
```bash
make redis-info
```

#### Vider le cache complètement
```bash
make redis-flush
```

#### Se connecter au CLI Redis
```bash
make redis-connect
```

---

### 5. 🤖 ML Model Commands

#### Entraîner le modèle de détection de fraude
```bash
make ml-train
```
Lance l'entraînement avec les données Kaggle dans [artifacts/data/](../artifacts/data/).

#### Tester une prédiction
```bash
make ml-test
```
Envoie une requête de test au service model-serving.

#### Lister les modèles disponibles
```bash
make ml-list
```

---

### 6. 🏥 Health & Testing

#### Vérifier la santé de tous les services
```bash
make health
```
Teste PostgreSQL, Redis, et les 3 services Python (decision, model, rules).

Exemple de sortie :
```
PostgreSQL: ✅ HEALTHY
Redis: ✅ HEALTHY
Decision Engine: ✅ HEALTHY
Model Serving: ✅ HEALTHY
Rules Service: ✅ HEALTHY
```

#### Lancer les tests unitaires
```bash
make test
```

#### Lancer les tests end-to-end
```bash
make test-e2e
```

---

### 7. 🚀 Setup

#### Setup complet pour nouveau PC
```bash
make setup
```

Ce workflow fait :
1. `make up` - Démarre tous les services
2. `make db-migrate` - Applique les migrations
3. `make health` - Vérifie que tout fonctionne
4. Affiche les URLs des services

Sortie typique :
```
✅ Setup complete!

Services are running:
  - Decision Engine: http://localhost:8000
  - Model Serving:   http://localhost:8001
  - Rules Service:   http://localhost:8002

Try: make ml-test
```

#### Vérifier le statut du setup
```bash
make check
```
Lance le script [check-setup.sh](../check-setup.sh) qui vérifie Python, Docker, données Kaggle, etc.

---

## Workflows Complets

### Premier démarrage sur un nouveau PC

```bash
# 1. Vérifier les prérequis
make check

# 2. Setup complet
make setup

# 3. Tester
make ml-test

# 4. Voir les logs
make logs
```

### Développement quotidien

```bash
# Démarrer
make up

# Voir les logs pendant le dev
make logs-decision

# Tester après modifications
make rebuild
make test

# Arrêter à la fin
make down
```

### Debug d'un problème

```bash
# 1. Vérifier la santé
make health

# 2. Voir les logs du service problématique
make logs-model

# 3. Vérifier Kafka
make kafka-consume

# 4. Regarder la DB
make db-connect
# puis dans psql:
SELECT * FROM fraud_cases ORDER BY created_at DESC LIMIT 10;
```

### Mise à jour du modèle ML

```bash
# 1. Entraîner nouveau modèle
make ml-train

# 2. Rebuild le service
make rebuild

# 3. Tester
make ml-test

# 4. Vérifier les logs
make logs-model
```

### Nettoyage complet

```bash
# Tout supprimer et repartir de zéro
make clean
make setup
```

---

## Comparaison Make vs Scripts Shell

| Tâche | Avec Make | Avec Scripts Shell |
|-------|-----------|-------------------|
| Démarrer services | `make up` | `./scripts/docker-helper.sh start` |
| Voir logs d'un service | `make logs-decision` | `./scripts/docker-helper.sh logs decision-engine` |
| Migrations DB | `make db-migrate` | `./scripts/db-helper.sh migrate` |
| Lister topics Kafka | `make kafka-list` | `./scripts/kafka-helper.sh list` |
| Entraîner modèle | `make ml-train` | `python scripts/train_fraud_model_kaggle.py` |
| Setup complet | `make setup` | Enchaîner 5-6 commandes manuellement |

**Conclusion** : `make` est plus court et plus facile à retenir !

---

## Personnalisation

Vous pouvez ajouter vos propres commandes dans le [Makefile](../Makefile).

Exemple - ajouter une commande pour voir les métriques Prometheus :

```makefile
metrics:
	@echo "Opening Prometheus..."
	@open http://localhost:9090
```

Puis utilisez `make metrics`.

---

## Astuces

### 1. Autocomplétion
Bash supporte l'autocomplétion avec `make` :
```bash
make db-<TAB>  # Affiche db-migrate, db-reset, db-stats, db-connect
```

### 2. Exécution multiple
Vous pouvez chaîner des commandes :
```bash
make down clean up db-migrate
```

### 3. Voir ce qui se passe
Retirez le `@` devant une commande pour voir ce qu'elle exécute :
```makefile
# Avant
db-migrate:
	@./scripts/db-helper.sh migrate

# Après (pour debug)
db-migrate:
	./scripts/db-helper.sh migrate
```

---

## Dépendances entre commandes

Certaines commandes ont des **dépendances automatiques** :

```makefile
setup: up db-migrate health
```

Cela signifie que `make setup` exécute automatiquement :
1. `make up`
2. `make db-migrate`
3. `make health`

---

## FAQ

### Pourquoi utiliser Make plutôt qu'un script Python ou npm scripts ?

✅ **Standard Unix** : Make est installé partout
✅ **Simplicité** : Syntaxe simple pour des tâches simples
✅ **Pas de dépendances** : Pas besoin d'installer Node.js ou Python en plus
✅ **Performances** : Make peut paralléliser les tâches

### Puis-je utiliser Make sous Windows ?

Oui, avec :
- **Git Bash** (recommandé, inclus avec Git)
- **WSL** (Windows Subsystem for Linux)
- **Chocolatey** : `choco install make`

### Et si je préfère les scripts shell ?

Aucun problème ! Les scripts dans [scripts/](../scripts/) sont autonomes. `make` les appelle simplement.

---

## Résumé des Commandes les Plus Utiles

```bash
# Top 10 des commandes quotidiennes
make up              # Démarrer
make down            # Arrêter
make logs            # Voir les logs
make health          # Vérifier la santé
make db-migrate      # Migrations DB
make ml-test         # Tester le modèle
make test            # Tests unitaires
make rebuild         # Rebuild après modifs
make setup           # Setup complet
make help            # Liste complète
```

Gardez cette page sous la main et vous serez ultra-productif ! 🚀
