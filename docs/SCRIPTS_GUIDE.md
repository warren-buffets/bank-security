# Guide des Scripts Helper - SafeGuard

Ce guide explique l'utilité de tous les scripts shell présents dans le dossier [scripts/](../scripts/).

## Vue d'ensemble

Les scripts helper sont des outils de ligne de commande qui simplifient les opérations courantes de développement et de déploiement. Ils automatisent les tâches répétitives et fournissent une interface simple pour gérer l'infrastructure.

## Scripts disponibles

### 1. [db-helper.sh](../scripts/db-helper.sh) - Gestion de la base de données PostgreSQL

**Utilité** : Facilite les opérations sur la base de données PostgreSQL (migrations, requêtes, monitoring).

**Commandes principales** :
```bash
./scripts/db-helper.sh migrate       # Appliquer les migrations SQL
./scripts/db-helper.sh connect       # Se connecter à psql
./scripts/db-helper.sh reset         # Réinitialiser la base (DROP + migrations)
./scripts/db-helper.sh stats         # Afficher les statistiques (taille des tables)
./scripts/db-helper.sh query "SQL"   # Exécuter une requête SQL
```

**Exemples** :
```bash
# Appliquer toutes les migrations
./scripts/db-helper.sh migrate

# Voir les stats des tables
./scripts/db-helper.sh stats

# Compter les transactions frauduleuses
./scripts/db-helper.sh query "SELECT COUNT(*) FROM transactions WHERE is_fraud = true"
```

---

### 2. [docker-helper.sh](../scripts/docker-helper.sh) - Gestion des conteneurs Docker

**Utilité** : Simplifie les opérations Docker Compose (démarrage, arrêt, logs, rebuild).

**Commandes principales** :
```bash
./scripts/docker-helper.sh start              # Démarrer tous les services
./scripts/docker-helper.sh stop               # Arrêter tous les services
./scripts/docker-helper.sh restart            # Redémarrer tous les services
./scripts/docker-helper.sh logs [service]     # Voir les logs (tous ou un service)
./scripts/docker-helper.sh ps                 # Statut des conteneurs
./scripts/docker-helper.sh rebuild [service]  # Rebuild un service
./scripts/docker-helper.sh clean              # Nettoyer (volumes, images inutilisées)
```

**Exemples** :
```bash
# Démarrer tous les services
./scripts/docker-helper.sh start

# Voir les logs du decision-engine en temps réel
./scripts/docker-helper.sh logs decision-engine

# Rebuild le service model-serving après des modifications
./scripts/docker-helper.sh rebuild model-serving
```

---

### 3. [k8s-helper.sh](../scripts/k8s-helper.sh) - Déploiement Kubernetes

**Utilité** : Gère le déploiement sur Kubernetes (via manifests ou Helm).

**Commandes principales** :
```bash
./scripts/k8s-helper.sh apply          # Appliquer les manifests K8s
./scripts/k8s-helper.sh deploy         # Déployer avec Helm
./scripts/k8s-helper.sh status         # Statut des pods
./scripts/k8s-helper.sh logs [pod]     # Logs d'un pod
./scripts/k8s-helper.sh delete         # Supprimer le déploiement
./scripts/k8s-helper.sh port-forward   # Forwarding de ports
```

**Exemples** :
```bash
# Déployer avec Helm
./scripts/k8s-helper.sh deploy

# Vérifier le statut des pods
./scripts/k8s-helper.sh status

# Voir les logs du decision-engine
./scripts/k8s-helper.sh logs decision-engine
```

---

### 4. [kafka-helper.sh](../scripts/kafka-helper.sh) - Gestion Kafka

**Utilité** : Opérations sur Kafka (topics, consommation de messages, production).

**Commandes principales** :
```bash
./scripts/kafka-helper.sh list                      # Lister tous les topics
./scripts/kafka-helper.sh create <topic>            # Créer un topic
./scripts/kafka-helper.sh describe <topic>          # Décrire un topic
./scripts/kafka-helper.sh consume <topic>           # Consommer des messages
./scripts/kafka-helper.sh produce <topic> <message> # Produire un message
./scripts/kafka-helper.sh delete <topic>            # Supprimer un topic
```

**Exemples** :
```bash
# Lister tous les topics
./scripts/kafka-helper.sh list

# Consommer les événements de fraude en temps réel
./scripts/kafka-helper.sh consume fraud-events

# Créer un nouveau topic avec 5 partitions
./scripts/kafka-helper.sh create test-topic 5
```

---

### 5. [ml-helper.sh](../scripts/ml-helper.sh) - Gestion des modèles ML

**Utilité** : Opérations sur les modèles de Machine Learning (entraînement, test, métriques).

**Commandes principales** :
```bash
./scripts/ml-helper.sh list           # Lister les modèles disponibles
./scripts/ml-helper.sh info [model]   # Info sur un modèle
./scripts/ml-helper.sh test           # Tester une prédiction
./scripts/ml-helper.sh train          # Entraîner un nouveau modèle
./scripts/ml-helper.sh evaluate       # Évaluer les performances
./scripts/ml-helper.sh compare        # Comparer plusieurs modèles
```

**Exemples** :
```bash
# Lister les modèles disponibles
./scripts/ml-helper.sh list

# Tester une prédiction
./scripts/ml-helper.sh test

# Entraîner un nouveau modèle
./scripts/ml-helper.sh train

# Comparer les performances de plusieurs modèles
./scripts/ml-helper.sh compare
```

---

### 6. [redis-helper.sh](../scripts/redis-helper.sh) - Gestion Redis

**Utilité** : Opérations sur Redis (cache, monitoring, debug).

**Commandes principales** :
```bash
./scripts/redis-helper.sh connect           # Se connecter au CLI Redis
./scripts/redis-helper.sh ping              # Tester la connexion
./scripts/redis-helper.sh info              # Infos du serveur Redis
./scripts/redis-helper.sh keys [pattern]    # Lister les clés
./scripts/redis-helper.sh get <key>         # Obtenir une valeur
./scripts/redis-helper.sh flush             # Vider le cache
./scripts/redis-helper.sh monitor           # Monitorer les commandes en temps réel
```

**Exemples** :
```bash
# Vérifier la connexion Redis
./scripts/redis-helper.sh ping

# Voir toutes les clés de cache
./scripts/redis-helper.sh keys "*"

# Vider le cache complètement
./scripts/redis-helper.sh flush

# Monitorer les opérations Redis en temps réel
./scripts/redis-helper.sh monitor
```

---

### 7. [retrain.sh](../scripts/retrain.sh) - Ré-entraînement automatique

**Utilité** : Script complet pour ré-entraîner le modèle avec de nouvelles données.

**Workflow** :
1. Sauvegarde du modèle actuel
2. Chargement des nouvelles données
3. Entraînement du nouveau modèle
4. Évaluation des performances
5. Déploiement si les métriques sont meilleures
6. Rollback automatique si dégradation

**Usage** :
```bash
./scripts/retrain.sh                    # Ré-entraînement complet
./scripts/retrain.sh --dry-run          # Simulation sans déploiement
./scripts/retrain.sh --force            # Forcer le déploiement
```

---

## Pourquoi ces scripts ?

### 1. **Productivité**
- Évite de taper des commandes longues et complexes
- Réduit les erreurs humaines
- Automatise les workflows répétitifs

### 2. **Cohérence**
- Standardise les opérations entre les développeurs
- Documentation vivante (les scripts montrent comment faire)
- Bonnes pratiques intégrées

### 3. **Onboarding**
- Les nouveaux développeurs peuvent être productifs rapidement
- Pas besoin de mémoriser 50 commandes Docker/Kubernetes/Kafka
- Interface unifiée et intuitive

### 4. **Production Ready**
- Scripts testés et robustes
- Gestion d'erreurs intégrée
- Logs colorés et informatifs

---

## Exemples de workflows complets

### Démarrage local complet
```bash
# 1. Démarrer l'infrastructure
./scripts/docker-helper.sh start

# 2. Appliquer les migrations DB
./scripts/db-helper.sh migrate

# 3. Vérifier que Kafka fonctionne
./scripts/kafka-helper.sh list

# 4. Tester le modèle ML
./scripts/ml-helper.sh test
```

### Debug d'un problème de fraude
```bash
# 1. Vérifier les logs du decision-engine
./scripts/docker-helper.sh logs decision-engine

# 2. Voir les messages Kafka
./scripts/kafka-helper.sh consume fraud-events

# 3. Vérifier le cache Redis
./scripts/redis-helper.sh keys "idempotency:*"

# 4. Requêter la base de données
./scripts/db-helper.sh query "SELECT * FROM fraud_cases ORDER BY created_at DESC LIMIT 10"
```

### Mise à jour du modèle ML
```bash
# 1. Entraîner un nouveau modèle
./scripts/ml-helper.sh train

# 2. Comparer avec l'ancien
./scripts/ml-helper.sh compare

# 3. Rebuild le service model-serving
./scripts/docker-helper.sh rebuild model-serving

# 4. Tester
./scripts/ml-helper.sh test
```

---

## Convention de nommage

Tous les scripts suivent le pattern : `<service>-helper.sh`

- `db-helper.sh` : Base de données
- `docker-helper.sh` : Docker Compose
- `k8s-helper.sh` : Kubernetes
- `kafka-helper.sh` : Kafka
- `ml-helper.sh` : Machine Learning
- `redis-helper.sh` : Redis Cache

---

## Personnalisation

Les scripts utilisent des variables d'environnement que vous pouvez customiser :

```bash
# Dans votre .env ou export dans le terminal
export POSTGRES_HOST=my-db-server.com
export KAFKA_BOOTSTRAP_SERVERS=my-kafka:9092
export K8S_NAMESPACE=production

# Ensuite les scripts utiliseront ces valeurs
./scripts/db-helper.sh connect
```

---

## Besoin d'aide ?

Chaque script affiche son aide avec :
```bash
./scripts/db-helper.sh help
./scripts/docker-helper.sh help
# etc.
```
