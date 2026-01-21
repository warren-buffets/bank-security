# FraudGuard - Six-Pager Technique

## 1. Résumé Exécutif

### Problème
Les institutions financières font face à des pertes massives dues à la fraude bancaire. Les systèmes traditionnels basés sur des règles statiques sont insuffisants face à l'évolution des techniques de fraude. Le défi est de détecter les transactions frauduleuses en temps réel tout en minimisant les faux positifs qui impactent l'expérience client.

### Solution Proposée
FraudGuard est une plateforme de détection de fraude en temps réel combinant :
- **Machine Learning** (LightGBM) pour la détection de patterns complexes
- **Moteur de règles** pour les cas métier explicites
- **Architecture microservices** pour la scalabilité et la maintenabilité

### Portée
- Analyse de transactions bancaires en temps réel (<100ms de latence)
- Scoring de risque avec probabilité calibrée
- Gestion des cas de fraude détectés
- Monitoring et observabilité complète

### Résultats Attendus
| Métrique | Cible |
|----------|-------|
| AUC-ROC | > 0.95 |
| Taux de faux positifs | < 1% |
| Latence P99 | < 100ms |
| Disponibilité | 99.9% |

---

## 2. Contexte & Principes

### Contraintes
- **Temps réel** : Décision en <100ms pour ne pas impacter l'expérience utilisateur
- **Volume** : Capacité de traiter 10K+ transactions/seconde
- **Réglementation** : Conformité RGPD (données personnelles hashées)
- **Coût** : Infrastructure cloud-native optimisée

### Hypothèses
- Les patterns de fraude évoluent → modèle re-entraînable
- 99%+ des transactions sont légitimes → déséquilibre de classes
- Les features géographiques (IP) sont importantes pour la détection

### Exigences Non Fonctionnelles
| Catégorie | Exigence |
|-----------|----------|
| Performance | Latence P50 < 50ms, P99 < 100ms |
| Scalabilité | Horizontal scaling via Kubernetes |
| Fiabilité | Circuit breaker, retry, fallback |
| Sécurité | Données sensibles hashées, TLS partout |
| Observabilité | Métriques, logs, traces distribuées |

### Principes Guidants (Tenets)
1. **La sécurité du client prime** : En cas de doute, mieux vaut un faux positif qu'une fraude non détectée
2. **Explicabilité** : Chaque décision doit être justifiable (audit trail)
3. **Évolutivité** : Le système doit s'adapter aux nouvelles menaces
4. **Simplicité opérationnelle** : Déploiement et monitoring accessibles

---

## 3. Design Proposé

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Load Balancer                                │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Decision Engine (8000)                          │
│                      - Orchestration                                 │
│                      - Agrégation des scores                         │
│                      - Décision finale                               │
└─────────────────────────────────────────────────────────────────────┘
                    │                           │
         ┌──────────┴──────────┐    ┌──────────┴──────────┐
         ▼                     ▼    ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Model Serving  │  │  Rules Service  │  │  Case Service   │
│     (8001)      │  │     (8002)      │  │     (8003)      │
│  - LightGBM     │  │  - Règles métier│  │  - Gestion cas  │
│  - Scoring ML   │  │  - Listes noires│  │  - Workflow     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └──────────┬──────────┴──────────┬──────────┘
                    ▼                     ▼
              ┌──────────┐         ┌──────────┐
              │  Redis   │         │ Postgres │
              │ (cache)  │         │  (data)  │
              └──────────┘         └──────────┘
                    │
                    ▼
              ┌──────────┐
              │  Kafka   │
              │ (events) │
              └──────────┘
```

### Flux de Traitement

```
1. Transaction entrante
       │
       ▼
2. Decision Engine reçoit la requête
       │
       ├──► 3a. Model Serving : scoring ML (0.0-1.0)
       │
       └──► 3b. Rules Service : vérification règles
                 - Listes noires (IP, merchant, card)
                 - Règles de vélocité
                 - Règles géographiques
       │
       ▼
4. Agrégation des scores
   - Score final = max(ML_score, Rules_score)
   - Calibration du score
       │
       ▼
5. Décision
   - APPROVE : score < 0.3
   - REVIEW  : 0.3 ≤ score < 0.7
   - BLOCK   : score ≥ 0.7
       │
       ▼
6. Si REVIEW/BLOCK → Case Service crée un dossier
       │
       ▼
7. Event Kafka pour audit trail
```

### Choix Technologiques

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| API Framework | FastAPI | Async, performant, OpenAPI natif |
| ML Model | LightGBM | Rapide, bon sur données tabulaires déséquilibrées |
| Message Queue | Kafka | Haute disponibilité, replay possible |
| Cache | Redis | Latence sub-ms, structures de données riches |
| Database | PostgreSQL | ACID, JSON support, maturité |
| Container | Docker + K8s | Standard industrie, scaling horizontal |
| Monitoring | Prometheus + Grafana | Open source, écosystème riche |

### Gestion des Données IP

**Option retenue : Hashing déterministe**

```python
import hashlib

def hash_ip(ip: str, salt: str = "fraudguard") -> str:
    """Hash IP de manière déterministe pour anonymisation RGPD."""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]

# Même IP → même hash → permet l'agrégation sans exposer l'IP réelle
```

**Enrichissement optionnel via WHOIS/GeoIP** :
- Pays, ASN, type de réseau (residential, datacenter, VPN)
- Stocké hashé, enrichissement en mémoire uniquement

### Métriques ML

#### AUC-ROC (Area Under Curve)
- Mesure la capacité du modèle à distinguer fraude/non-fraude
- Indépendant du seuil de décision
- **Cible : > 0.95**

#### Taux de Faux Positifs (FPR)
- Transactions légitimes bloquées à tort
- Impact direct sur l'expérience client
- **Cible : < 1%**

#### Calibration
Ajuster les scores pour que la probabilité prédite corresponde à la réalité :
- Score 0.8 = 80% de chances réelles de fraude
- Utilisation de Platt Scaling ou Isotonic Regression
- Validation via Brier Score

```python
from sklearn.calibration import CalibratedClassifierCV

calibrated_model = CalibratedClassifierCV(
    base_model,
    method='isotonic',  # ou 'sigmoid' pour Platt
    cv=5
)
```

### Sécurité
- TLS 1.3 pour toutes les communications
- Secrets via Kubernetes Secrets / Vault
- Données PII hashées (IP, card number)
- Rate limiting par IP/client
- Audit log de toutes les décisions

### Observabilité

| Type | Outil | Métriques clés |
|------|-------|----------------|
| Metrics | Prometheus | Latence, throughput, error rate |
| Logs | Loki/ELK | Logs structurés JSON |
| Traces | Jaeger | Distributed tracing |
| Dashboards | Grafana | Vue unifiée |

---

## 4. Alternatives Évaluées

### Modèle ML

| Option | Avantages | Inconvénients | Verdict |
|--------|-----------|---------------|---------|
| **LightGBM** | Rapide, bon sur déséquilibré | Moins bon sur séquences | ✅ Retenu |
| XGBoost | Très populaire | Plus lent que LightGBM | ❌ |
| Neural Network | Patterns complexes | Latence, explicabilité | ❌ |
| Random Forest | Stable | Plus lent, moins précis | ❌ |

### Architecture

| Option | Avantages | Inconvénients | Verdict |
|--------|-----------|---------------|---------|
| **Microservices** | Scalable, indépendant | Complexité réseau | ✅ Retenu |
| Monolithe | Simple | Scaling difficile | ❌ |
| Serverless | Pay-per-use | Cold start, vendor lock | ❌ |

### Base de données

| Option | Avantages | Inconvénients | Verdict |
|--------|-----------|---------------|---------|
| **PostgreSQL** | ACID, maturité | Scaling horizontal complexe | ✅ Retenu |
| MongoDB | Flexible schema | Pas ACID par défaut | ❌ |
| Cassandra | Très scalable | Complexité opérationnelle | ❌ |

---

## 5. Risques & Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Drift du modèle ML | Haute | Haute | Monitoring AUC, re-training automatique |
| Latence dégradée | Moyenne | Haute | Circuit breaker, fallback sur règles |
| Faux positifs élevés | Moyenne | Haute | A/B testing, seuils ajustables |
| Indisponibilité Kafka | Basse | Moyenne | Mode dégradé sync, retry queue |
| Attaque DDoS | Moyenne | Haute | Rate limiting, WAF, auto-scaling |

### Plan de Repli
1. **Si Model Serving down** → Rules Service seul (mode dégradé)
2. **Si Redis down** → Bypass cache, requêtes directes
3. **Si latence > SLA** → Réponse par défaut configurable

### Tests et Validation
- Unit tests : >80% coverage
- Integration tests : API contracts
- Load tests : Locust, 10K req/s
- Chaos engineering : Network failures simulation

---

## 6. Plan & Métriques

### Phasage

| Phase | Durée | Livrables |
|-------|-------|-----------|
| 1 - MVP | ✅ Done | Services core, modèle LightGBM, Docker |
| 2 - Production Ready | 2 sem | Tests complets, K8s, CI/CD |
| 3 - Observabilité | 1 sem | Grafana dashboards, alerting |
| 4 - Hardening | 1 sem | Sécurité, load testing, docs |

### Ressources

| Ressource | Quantité | Coût estimé/mois |
|-----------|----------|------------------|
| K8s nodes (3x) | 4 vCPU, 16GB RAM | ~$300 |
| PostgreSQL | 2 vCPU, 8GB RAM | ~$100 |
| Redis | 2GB | ~$30 |
| Kafka | 3 brokers | ~$150 |
| **Total** | | **~$580/mois** |

### OKRs

**Objective** : Déployer une plateforme de détection de fraude fiable

| Key Result | Cible | Mesure |
|------------|-------|--------|
| KR1 : Précision ML | AUC > 0.95 | Evaluation sur test set |
| KR2 : Latence | P99 < 100ms | Prometheus metrics |
| KR3 : Faux positifs | < 1% | Dashboard monitoring |
| KR4 : Disponibilité | 99.9% uptime | SLA monitoring |

### SLIs / SLAs

| SLI | SLA | Mesure |
|-----|-----|--------|
| Latence P99 | < 100ms | `histogram_quantile(0.99, ...)` |
| Error rate | < 0.1% | `rate(errors) / rate(requests)` |
| Availability | > 99.9% | `1 - (downtime / total_time)` |
| Throughput | > 1000 req/s | `rate(requests[1m])` |

---

## Annexes

### A. Diagramme de Séquence - Transaction

```
Client          Decision-Engine    Model-Serving    Rules-Service    Kafka
  │                    │                │                │            │
  │─── POST /predict ─►│                │                │            │
  │                    │                │                │            │
  │                    │── GET /score ─►│                │            │
  │                    │◄── {score} ────│                │            │
  │                    │                │                │            │
  │                    │── GET /check ──────────────────►│            │
  │                    │◄── {rules} ────────────────────│            │
  │                    │                │                │            │
  │                    │── aggregate & decide ──────────►│            │
  │                    │                │                │            │
  │                    │── publish event ───────────────────────────►│
  │                    │                │                │            │
  │◄── {decision} ────│                │                │            │
  │                    │                │                │            │
```

### B. Features du Modèle ML

| Feature | Type | Description |
|---------|------|-------------|
| amount | float | Montant de la transaction |
| hour | int | Heure de la transaction (0-23) |
| day_of_week | int | Jour de la semaine (0-6) |
| merchant_category | cat | Catégorie du marchand |
| ip_hash | str | Hash de l'IP (anonymisé) |
| card_country | cat | Pays de la carte |
| merchant_country | cat | Pays du marchand |
| velocity_1h | int | Nb transactions dernière heure |
| velocity_24h | int | Nb transactions 24h |
| amount_zscore | float | Écart au montant moyen du client |

### C. Règles Métier

```yaml
rules:
  - name: blacklisted_ip
    condition: ip_hash IN blacklist_ips
    action: BLOCK

  - name: high_velocity
    condition: velocity_1h > 10
    action: REVIEW

  - name: cross_border_high_amount
    condition: card_country != merchant_country AND amount > 1000
    action: REVIEW

  - name: night_transaction
    condition: hour BETWEEN 2 AND 5 AND amount > 500
    action: REVIEW
```
