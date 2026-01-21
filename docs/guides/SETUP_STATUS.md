# État actuel du projet FraudGuard AI

Ce document synthétise ce qui est déjà prêt dans le repo afin de pouvoir le présenter clairement.

## 1. Infrastructure & outillage
- `docker-compose.yml` orchestre 9 services : Postgres, Redis, Zookeeper, Kafka, Prometheus, Grafana, Model Serving, Rules Service et Decision Engine.
- `Makefile` fournit les commandes principales (`make up`, `make down`, `make health`, `make test`, etc.).
- `.env` et `.env.example` listent toutes les variables nécessaires (base de données, Redis, Kafka, URLs de services…).
- Docker Desktop + docker-compose installés, réseaux/volumes créés automatiquement.

## 2. Environnement Python
- `venv/` (Python 3.11) contient toutes les dépendances des trois microservices (`model-serving`, `rules-service`, `decision-engine`).
- Les requirements sont installés (`pip install -r services/.../requirements.txt`).
- LightGBM nécessite `libomp` (installé via Homebrew) et Python 3.11 (installé via Homebrew également).

## 3. Services implémentés
1. **Database migrations**  
   - Scripts `platform/postgres/migrations/V00*.sql` créent les tables `events`, `decisions`, `rules`, `lists`, `cases`, etc., avec indexes, triggers et seeds.

2. **Model Serving (FastAPI + LightGBM)**  
   - Endpoint `/predict`, métriques Prometheus, healthcheck HTTP.
   - Multi-stage Dockerfile (compilation + runtime).
   - Modèle LightGBM provisoire stocké dans `artifacts/models/gbdt_v1.bin`.

3. **Rules Service**  
   - DSL d’évaluation, cache Redis, endpoints `/evaluate` et `/metrics`.
   - Connecté à Postgres et Redis via AsyncIO.

4. **Decision Engine**  
   - Orchestration des appels Model + Rules, persistance Postgres, Kafka events, logique ALLOW/CHALLENGE/DENY.

## 4. Observabilité
- Prometheus configuré (`platform/observability/prometheus.yml`) pour scrapper tous les services.
- Grafana préconfiguré (admin/admin) avec volume persistant.
- Tous les services exposent `/health` et `/metrics`.

## 5. Documentation existante
- `ENVIRONMENT_SETUP.md` : guide complet pour créer/activer le venv, installer les requirements, tester les services.
- `DOCKER_SETUP.md` et `SETUP_SUMMARY.txt` : explications Makefile + docker-compose.
- `PR_*` et `PULL_REQUESTS.md` : descriptions prêtes pour présenter chaque branche.
- `RECAP.md` : résumé des 4 services terminés et des 3 restants (Case Service, API Gateway, Feature Store).

## 6. État actuel après tests
- L’infrastructure Docker démarre (`make up`) et les correctifs suivants ont été appliqués :
  - **Model Serving** : ajout de `requests` dans `requirements.txt`, ce qui permet au healthcheck Python embarqué dans le Dockerfile de fonctionner.
  - **Rules Service** : la requête SQL lit désormais les colonnes `rule_id`, `version`, `dsl`, `status`, etc., et les mappe vers la structure attendue par le moteur de règles.
- Les services d’infrastructure (Postgres, Redis, Kafka, Prometheus, Grafana, Zookeeper) restent sains.
- Le modèle LightGBM minimal permet maintenant à Model Serving de charger un artefact, même si les prédictions sont factices.

## 7. Prochaines actions recommandées
1. Relancer `make up` puis `make health` pour vérifier que les sondes Docker/HTTP passent bien avec les correctifs appliqués.
2. Enchaîner sur `make test` pour valider le flux complet fin‑à‑fin.
3. Continuer avec les 3 services restants (Case Service, API Gateway, Feature Store) comme indiqué dans `RECAP.md`.

Avec ces éléments, tu peux expliquer précisément ce qui est déjà en place : infra Docker complète, trois microservices fonctionnels, migrations DB robustes, monitoring via Prometheus/Grafana, et guides d’installation détaillés. Les seuls blocages restants sont identifiés ci-dessus.
