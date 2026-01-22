# Architecture Technique - FraudGuard AI

## 🎯 Vision

**FraudGuard AI** est un moteur antifraude temps réel qui analyse chaque paiement par carte en **moins de 100ms** et décide : **ALLOW** (autoriser), **CHALLENGE** (vérifier avec 2FA si nécessaire), ou **DENY** (bloquer).

### Objectifs clés

- **P95 < 100ms** : Décision temps réel sans ralentir le paiement
- **94% détection** : Identifier les vraies fraudes
- **< 2% faux positifs** : Minimiser friction client légitime
- **10k TPS** : Scalable à 50k+ transactions/seconde

---

## 🏗️ Composants principaux

### Vue d'ensemble

```
┌─────────────────────────────────────────────┐
│         APPLICATIONS CLIENTES               │
│   (App bancaire, E-commerce, POS, ATM)     │
└──────────────────┬──────────────────────────┘
                   │ HTTPS POST /v1/score
                   ▼
┌──────────────────────────────────────────────┐
│         DECISION ENGINE (Orchestrateur)      │
│                                              │
│  1. Vérification idempotence (Redis)        │
│  2. Feature engineering temps réel          │
│  3. Appels parallèles:                      │
│     • Rules Service                         │
│     • Model Serving (ML)                    │
│  4. Agrégation décision                     │
│  5. Persistance + Événements                │
└────────┬─────────────────────┬───────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐    ┌──────────────────┐
│ RULES SERVICE   │    │ MODEL SERVING    │
│                 │    │                  │
│ • Règles DSL    │    │ • ML LightGBM    │
│ • Listes deny   │    │ • Score [0..1]   │
│ • Vélocités     │    │ • Features top-k │
│ • Timeout: 50ms │    │ • Timeout: 30ms  │
└─────────────────┘    └──────────────────┘
         │                     │
         └──────────┬──────────┘
                    ▼
          ┌──────────────────┐
          │  FEATURE STORE   │
          │  (Redis)         │
          │                  │
          │ • Vélocités      │
          │ • Flags device   │
          │ • TTL 1h-24h     │
          └──────────────────┘

┌──────────────────────────────────────────────┐
│              COUCHE DONNÉES                  │
│                                              │
│  POSTGRES                 KAFKA              │
│  • events                 • decision_events  │
│  • decisions              • case_events      │
│  • rules                  • analytics        │
│  • cases                                     │
│  • labels                                    │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│         CASE MANAGEMENT (Analystes)          │
│                                              │
│  • Case Service (Kafka consumer)            │
│  • Case UI (Interface analystes)            │
│  • Investigation + Labélisation             │
└──────────────────────────────────────────────┘
```
---

## ⚙️ Logique de décision

### Règles de base

**1. Score ML (0 à 1)** :
- **< 0.50** : Risque faible
- **0.50 - 0.70** : Risque moyen
- **> 0.70** : Risque élevé

**2. Décision finale** :

| Score | Règles critiques | 2FA initial | Décision |
|-------|-----------------|-------------|----------|
| < 0.50 | Non | - | **ALLOW** |
| 0.50-0.70 | Non | ❌ Non | **CHALLENGE** → Demander 2FA |
| 0.50-0.70 | Non | ✅ Oui | **ALLOW** (2FA suffit) |
| > 0.70 | - | - | **CHALLENGE** ou **DENY** |
| Quelconque | ✅ Oui (pays sanctionné, TOR, AML) | - | **DENY** |

### Logique CHALLENGE + 2FA

**Principe clé** :
> Si 2FA manque ET risque détecté → Le demander
> Si 2FA présent ET risque modéré → L'utiliser (pas de doublon)

**Exemples** :

**Cas 1 : E-commerce 850€ (pas de 2FA initial)**
```
Score : 0.62 → CHALLENGE détecté
2FA initial ? NON (e-commerce standard)
→ Demander 2FA : "Confirmez 850€ vers Merchant X"
→ Client entre code SMS
→ Transaction acceptée
```

**Cas 2 : Virement app bancaire 850€ (2FA déjà validé)**
```
Score : 0.62 → CHALLENGE détecté
2FA initial ? OUI (virement > 500€)
→ 2FA déjà validé → Sécurité OK
→ Transaction acceptée (pas de re-demande)
```

**Cas 3 : Crypto 3000€ RU (risque extrême)**
```
Score : 0.89 → Très élevé
Règles : pays sanctionné + crypto + montant élevé
→ DENY immédiat (même avec 2FA)
→ Case analyste créé
```

---

## 🗄️ Schéma données (simplifié)

### Vue d'ensemble des tables

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   events     │       │  decisions   │       │    cases     │
│              │       │              │       │              │
│ PK: event_id │◄──────┤ FK: event_id │◄──────┤ FK: event_id │
│              │       │              │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
                                                      │
                       ┌──────────────┐              │
                       │    labels    │              │
                       │              │              │
                       │ FK: event_id │◄─────────────┘
                       │              │
                       └──────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    rules     │       │    lists     │       │  audit_logs  │
│              │       │              │       │              │
│ PK: rule_id  │       │ PK: compound │       │ PK: log_id   │
│              │       │              │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
```

### Tables principales

**events** (Source de vérité)
- `event_id` : ID unique transaction
- `tenant_id` : Multi-tenant
- `payload_json` : Données complètes transaction (JSONB)
- `idem_key` : Clé idempotence (TTL 24h)
- `hash` : SHA-256 pour intégrité

**decisions** (Immutable - audit trail)
- `decision_id` : ID unique décision
- `event_id` : Référence transaction
- `decision` : ALLOW | CHALLENGE | DENY
- `score` : Score ML [0..1]
- `rule_hits` : Liste règles déclenchées
- `reasons` : Raisons explicables
- `latency_ms` : Temps traitement
- `model_version` : Version modèle ML

**cases** (Investigation analystes)
- `case_id` : ID unique case
- `event_id` : Référence transaction
- `queue` : high_risk | medium_risk | review
- `status` : open | in_progress | closed
- `assignee` : Analyste assigné
- `priority` : 0 (low) | 1 (medium) | 2 (high)
- `resolution` : fraud_confirmed | legit | false_positive

**labels** (Feedback loop ML)
- `event_id` : Référence transaction
- `label` : fraud | legit | chargeback | fp
- `source` : analyst | customer | chargeback_system
- Utilisé pour retraining modèle

**rules** (Versionnées)
- `rule_id` : ID règle
- `version` : Numéro version
- `dsl` : Expression règle (DSL)
- `status` : draft | published | disabled

**lists** (Allow/Deny)
- `list_id` : deny_ip | deny_device | allow_merchant
- `type` : allow | deny | monitor
- `value` : IP, device_id, merchant_id

**audit_logs** (Immutable - compliance)
- `log_id` : ID séquentiel
- `actor` : Qui a fait l'action
- `action` : CREATE | UPDATE | DELETE
- `entity` : Table concernée
- `before/after` : État avant/après (JSONB)
- `signature` : HMAC-SHA256
- Rétention 7 ans (compliance)

---

## 🧠 Machine Learning

### Modèle : Gradient Boosting (GBDT)

**Choix LightGBM/XGBoost** :
- Performance : AUC 0.93 sur données tabulaires
- Latence : 10-20ms (vs 200ms+ Deep Learning)
- Explicabilité : SHAP values
- Data efficiency : 10k-100k exemples suffisent

**Features principales (50-100)** :

**Vélocités** :
- tx_per_5min, tx_per_1h, sum_amount_24h

**Contexte** :
- new_device (< 90j), geo_mismatch, proxy_vpn_flag

**Profil** :
- account_age_days, prev_chargebacks, kyc_confidence

**Marchand** :
- mcc_risk_score, merchant_seen_before

**Patterns** :
- amount_zscore, split_payment_flag

### Pipeline ML

```
1. Données historiques (events + labels)
   ↓
2. Feature engineering offline
   ↓
3. Training GBDT (LightGBM)
   ↓
4. Calibration Platt/Isotonic
   ↓
5. Optimisation seuils (coût FP vs FN)
   ↓
6. Validation (AUC, backtesting)
   ↓
7. Déploiement canary 10%
   ↓
8. Monitoring drift 48h
   ↓
9. Promotion 100% si OK
```

**Fréquence retraining** : 1x/semaine minimum

---

## ⚡ Budget latence (P95 < 100ms)

| Composant | Latence | Justification |
|-----------|---------|---------------|
| **Decision Engine** | 15ms | Orchestration, validation |
| **Model Serving** | 20ms | Inférence GBDT optimisée |
| **Rules Service** | 30ms | Évaluation règles + Redis |
| **Redis queries** | 5ms | 3-5 GET/SET (features) |
| **Postgres INSERT** | 10ms | SSD, index optimisés |
| **Réseau client** | 20ms | CDN + géo-distribution |
| **Total P95** | **100ms** | Budget respecté ✅ |

### Optimisations

- **Appels parallèles** : Rules + Model simultanés
- **Cache Redis** : Features pré-calculées (vélocités)
- **Indexes Postgres** : (tenant_id, ts), (event_id)
- **GBDT compilé** : Treelite ou ONNX Runtime

---

## 🔒 Sécurité et conformité

### RGPD

**Minimization PII** :
- Pas de PAN (tokenisation)
- IP/device hashés dans logs
- Rétention : 90j online, 2 ans archive
- Droit à l'oubli implémenté

**Audit trail** :
- Table `audit_logs` immutable (WORM)
- Signature HMAC-SHA256 par log
- Chaînage hash (blockchain-like)
- Rétention 7 ans (compliance)

### PSD2 (Europe)

**SCA (Strong Customer Authentication)** :
- 2FA lié à la transaction (montant, bénéficiaire)
- Exemptions low-value supportées (< 30€ + risque faible)
- Transaction Risk Analysis (TRA) implémenté

**Notre implémentation** :
- CHALLENGE déclenche 2FA si manquant
- Réutilise 2FA existant si présent
- Conforme SCA dynamique

---

## 📊 Workflow analystes

### Flux automatique

```
Transaction CHALLENGE/DENY
         ↓
Kafka → Case Service
         ↓
Création case (queue + priorité)
         ↓
Notification analystes
         ↓
Case UI : Investigation
         ↓
Décision analyste:
├─ APPROVE → Débloque + label "legit"
├─ REJECT → Bloque + label "fraud"
└─ CONTACT → SMS/Call client
         ↓
Case fermé + Label ML
```

### Interface Case UI

**Informations affichées** :
- Détails transaction (montant, marchand, pays)
- Score ML + top features contributives
- Règles déclenchées
- Profil utilisateur (historique, KYC)
- Vélocité (patterns suspects)
- Cases liés (historique utilisateur)

**Actions disponibles** :
- **Approuver** : Override ML, transaction passe
- **Rejeter** : Confirmer fraude, blocage permanent
- **Contacter** : Vérification client (SMS/Appel)
- **Labéliser** : fraud/legit/chargeback/fp

### Permissions

| Rôle | Queues | Montant max | PII |
|------|--------|-------------|-----|
| Analyst Junior | review, medium | 500€ | Masqué |
| Analyst Senior | Toutes | 10k€ | Complet |
| Fraud Manager | Toutes | Illimité | Complet |

---

## 🚀 Déploiement

### Développement (Docker Compose)

```bash
make up        # Démarre tous services
make health    # Vérifier santé
make logs      # Voir logs
make down      # Arrêter
```

**Services** :
- Postgres (5432)
- Redis (6379)
- Kafka (9092)
- Prometheus (9090)
- Grafana (3000)

### Production (Kubernetes)

**Scalabilité horizontale** :
- 3+ replicas Decision Engine (HPA)
- 2+ replicas Model Serving
- Redis Cluster (3 nodes)
- Postgres HA (primary + replicas)
- Kafka cluster (3 brokers)

**Sécurité** :
- mTLS entre services (Istio/Linkerd)
- Network policies
- Secrets management (KMS)
- Pod security policies

---

## 📈 Métriques et KPIs

### Performance

- **P95 latency** : < 100ms ✅
- **P99 latency** : < 150ms
- **Throughput** : 10k TPS (scalable 50k+)
- **Disponibilité** : 99.95%

### Qualité détection

- **True Positive Rate** : > 92%
- **False Positive Rate** : < 2%
- **AUC modèle** : > 0.90
- **Précision analystes** : 96.8% (avec revue)

### Business

- **Réduction fraude** : -75% vs règles seules
- **Réduction friction** : -50% faux positifs
- **Économie chargebacks** : ~15M€/an

---

## 🔄 Feedback loop (amélioration continue)

```
Analyste labélise transaction
         ↓
Label stocké (table labels)
         ↓
Pipeline batch nuit (Airflow)
         ↓
Retraining modèle (nouveaux labels)
         ↓
Validation (AUC, backtesting)
         ↓
Déploiement canary (10% trafic)
         ↓
Monitoring drift + métriques
         ↓
Promotion 100% si succès
         ↓
Amélioration 93% → 97% (itératif)
```

---

## 🎯 Résumé exécutif

### Architecture en 3 points

1. **Scoring temps réel** : ML (GBDT) + Règles métier en parallèle, décision < 100ms
2. **Logique intelligente** : CHALLENGE demande 2FA seulement si nécessaire (pas de doublon)
3. **Boucle d'apprentissage** : Labels analystes → Retraining ML → Amélioration continue

### Stack technique

- **Backend** : Python FastAPI
- **ML** : LightGBM/XGBoost (GBDT)
- **Data** : PostgreSQL + Redis + Kafka
- **Observabilité** : Prometheus + Grafana
- **Deploy** : Docker Compose (dev) + Kubernetes (prod)

### Valeur ajoutée

- **Sécurité** : 94% fraudes détectées
- **UX** : 2% faux positifs (vs 8-15% concurrence)
- **Conformité** : RGPD + PSD2 natif
- **Performance** : 100ms latence P95
