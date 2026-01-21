# Documentation FraudGuard AI - Index

## 🎯 Document Principal : Six-Pager

### [SIX_PAGER.md](SIX_PAGER.md) ⭐ **DOCUMENT DE RÉFÉRENCE**
**Six-Pager Technique complet** (format Amazon/Microsoft)
- Résumé exécutif (problème, solution, résultats attendus)
- Contexte & principes (contraintes, exigences, tenets)
- Design proposé (architecture, flux, choix techniques)
- Alternatives évaluées (options rejetées, trade-offs)
- Risques & mitigations (dépendances, fallbacks)
- Plan & métriques (phasage, OKRs, SLAs, coûts)

👉 **Document de soutenance - À lire en priorité**

---

## 📚 Documents principaux (3 fichiers essentiels)

### 1. [GUIDE-RAPIDE.md](GUIDE-RAPIDE.md) ⭐ COMMENCER ICI
**Démarrage en 3 minutes**
- Vue d'ensemble du système
- Comment ça marche (3 décisions : ALLOW/CHALLENGE/DENY)
- Logique CHALLENGE + 2FA
- Installation rapide
- Métriques clés
- FAQ

👉 **Lire en premier** pour comprendre le projet

---

### 2. [ARCHITECTURE.md](ARCHITECTURE.md) 🏗️ TECHNIQUE
**Architecture technique complète**
- Composants principaux (Decision Engine, Model Serving, Rules...)
- Logique de décision détaillée
- Schéma données (tables principales)
- Machine Learning (GBDT, features, pipeline)
- Budget latence (P95 < 100ms)
- Sécurité et conformité (RGPD, PSD2)
- Workflow analystes
- Déploiement (Docker Compose, Kubernetes)
- Métriques et KPIs

👉 **Pour comprendre** l'architecture et les choix techniques

---

### 3. [FLUX-DONNEES.md](FLUX-DONNEES.md) 🔄 FLUX
**Tous les flux de données**
- Flux 1 : Scoring temps réel (synchrone < 100ms)
- Flux 2 : Case Management (asynchrone)
- Flux 3 : Feature Store (temps réel)
- Flux 4 : ML Training Pipeline (offline)
- Flux 5 : Observabilité (monitoring)
- Volumétrie et performance
- Patterns utilisés (Event Sourcing, CQRS, Circuit Breaker...)

👉 **Pour comprendre** comment les données circulent

---

## 📊 Métriques & Choix Techniques

### [METRICS.md](METRICS.md) 📈
**KPI et Métriques ML**
- AUC-ROC (objectif ≥ 0.94)
- Taux de faux positifs (FPR < 2%)
- Calibration du modèle (Platt Scaling, Isotonic Regression)
- Métriques business (Precision, Recall, F1)
- Métriques opérationnelles (P95, P99, throughput)
- Dashboard de monitoring

### [IP_GEOLOCATION.md](IP_GEOLOCATION.md) 🌍
**Géolocalisation IP - Choix Technique**
- Problématique (performance, RGPD, précision)
- Option 1: Hash IP seul (anonymisation)
- Option 2: WHOIS/GeoIP (enrichissement)
- **Solution retenue**: Approche hybride (Hash + GeoLite2)
- Features ML extraites (pays, région, ASN, distance)
- Implémentation et performance
- RGPD compliance

---

## 🏗️ Architecture Decision Records (ADR)

### [adr/README.md](adr/README.md)
**Index des décisions architecturales**

#### ADRs Disponibles:
- [ADR-001: Architecture Microservices](adr/001-microservices-architecture.md)
- [ADR-002: Redis pour l'Idempotence](adr/002-redis-idempotency.md)
- [ADR-003: Moteur de Règles avec DSL](adr/003-rules-engine-dsl.md)

Chaque ADR documente :
- Contexte et problème
- Décision retenue
- Conséquences (positives/négatives)
- Alternatives évaluées et rejetées

---

## 📄 Documents complémentaires

### [database-schema.md](database-schema.md)
Schéma détaillé base de données PostgreSQL
- Tables : events, decisions, cases, labels, rules, lists
- Index et contraintes
- Volumétrie estimée
- Scripts SQL

### [api/openapi.yaml](api/openapi.yaml)
Spécification API complète (OpenAPI 3.0)
- Endpoint POST /v1/score
- Schémas requête/réponse
- Exemples

### [MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md) 🛠️
**Guide complet du Makefile**
- Commandes Docker (up, down, logs, rebuild)
- Commandes Database (migrate, reset, stats)
- Commandes Kafka, Redis, ML
- Workflows complets

### [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) 📜
**Guide des 7 scripts helper**
- db-helper.sh, docker-helper.sh, k8s-helper.sh
- kafka-helper.sh, ml-helper.sh, redis-helper.sh
- retrain.sh (ré-entraînement automatique)

---

## 🚀 Par où commencer ?

### Je découvre le projet
→ **[GUIDE-RAPIDE.md](GUIDE-RAPIDE.md)**

### Je veux comprendre l'architecture
→ **[ARCHITECTURE.md](ARCHITECTURE.md)**

### Je veux voir les flux de données
→ **[FLUX-DONNEES.md](FLUX-DONNEES.md)**

### Je veux le schéma BDD
→ **[database-schema.md](database-schema.md)**

### Je veux l'API
→ **[api/openapi.yaml](api/openapi.yaml)**

---

## 🎯 Résumé ultra-rapide

**FraudGuard AI** = Moteur antifraude temps réel

**3 décisions** :
- ✅ **ALLOW** : Score < 0.50 → Transaction passe
- ⚠️ **CHALLENGE** : Score 0.50-0.70 → 2FA si nécessaire
- ❌ **DENY** : Score > 0.70 → Blocage

**Performances** :
- P95 < 100ms
- 94% détection
- < 2% faux positifs

**Stack** :
- Python FastAPI + LightGBM/XGBoost
- PostgreSQL + Redis + Kafka
- Prometheus + Grafana

