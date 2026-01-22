# ML Fraud Detection Model - Six-Pager Technique

**Version** : 2.0
**Date** : Janvier 2025
**Équipe** : Warren Buffets
**Contact** : virgile.ader@epitech.digital

---

## 1. Résumé Exécutif

### Problème

Les systèmes de détection de fraude basés uniquement sur des règles statiques ont des limitations :
- **Taux de détection faible** (~70-80%)
- **Faux positifs élevés** (3-5%) → Frustration client
- **Pas d'apprentissage** → Les fraudeurs s'adaptent

### Solution Proposée

**Modèle LightGBM** entraîné sur le dataset Kaggle Credit Card Fraud (1.3M transactions) :

1. **12 features** : montant, heure, MCC, type de carte, distance géo, population urbaine
2. **Gradient Boosting** : LightGBM pour rapidité d'inférence (<10ms)
3. **Calibration** : Seuils de montant ajustés pour contexte bancaire européen

### Résultats

| Métrique | Valeur | Objectif |
|----------|--------|----------|
| **AUC-ROC** | 0.996 | > 0.94 ✅ |
| **Recall (Fraudes)** | 97% | > 90% ✅ |
| **Precision (Fraudes)** | 16% | > 10% ✅ |
| **Latence inférence** | < 5ms | < 30ms ✅ |

### Portée

**Implémenté (MVP)** :
- ✅ Modèle LightGBM entraîné et déployé
- ✅ 12 features incluant géolocalisation IP
- ✅ Seuils de montant ajustés (100€, 500€, 2000€)
- ✅ Intégration dans model-serving (FastAPI)

**Hors scope MVP** :
- ❌ Features de vélocité (transactions/24h)
- ❌ Détection de drift automatique
- ❌ Explicabilité SHAP

---

## 2. Contexte & Principes

### Dataset d'entraînement

**Source** : [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/datasets/kartik2112/fraud-detection)

| Caractéristique | Valeur |
|-----------------|--------|
| Transactions totales | 1,296,675 |
| Transactions frauduleuses | 7,506 (0.58%) |
| Période | Simulé |
| Origine | USA |

### Distribution des fraudes

| Catégorie de montant | Fraudes | Total | Taux |
|---------------------|---------|-------|------|
| < 100€ | 1,652 | 1,061,782 | **0.16%** |
| 100-500€ | 2,206 | 219,262 | **1.0%** |
| 500-2000€ | 3,648 | 14,900 | **24.5%** |
| > 2000€ | 0 | 731 | **0%** |

**Observation clé** : Les fraudes dans ce dataset sont concentrées sur les montants 500-2000€ (médiane fraude = 396€).

### Contraintes

1. **Latence** : Inférence < 30ms pour ne pas impacter l'expérience utilisateur
2. **Interprétabilité** : Features compréhensibles pour audit
3. **RGPD** : Pas de données personnelles dans le modèle

### Principes Guidants

1. **Simplicité** : Modèle GBDT plutôt que deep learning (plus rapide, interprétable)
2. **Fail safe** : Si ML échoue → fallback sur rules engine
3. **Observable** : Métriques Prometheus pour monitoring

---

## 3. Design Technique

### Architecture du modèle

```
┌─────────────────────────────────────────────────────────────┐
│                    Model Serving (Port 8001)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                Feature Engineering                    │   │
│  │                                                       │   │
│  │  Transaction ──► [amt, hour, day, mcc, card_type,    │   │
│  │                   channel, is_intl, is_night,        │   │
│  │                   is_weekend, amt_cat, dist_cat,     │   │
│  │                   city_pop]                          │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LightGBM Model (GBDT)                   │   │
│  │                                                       │   │
│  │  - 100 boosting rounds                               │   │
│  │  - 31 leaves per tree                                │   │
│  │  - scale_pos_weight: 171.75 (class imbalance)        │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│                   Fraud Score [0.0 - 1.0]                   │
└─────────────────────────────────────────────────────────────┘
```

### Features (12)

| # | Feature | Type | Description | Source |
|---|---------|------|-------------|--------|
| 1 | `amt` | float | Montant de la transaction | Request |
| 2 | `trans_hour` | int [0-23] | Heure de la transaction | Calculé |
| 3 | `trans_day` | int [0-6] | Jour de la semaine (0=Lundi) | Calculé |
| 4 | `merchant_mcc` | int | Code catégorie marchand | Request |
| 5 | `card_type` | int [0,1] | 0=physique, 1=virtuelle | Request |
| 6 | `channel` | int [0-3] | 0=app, 1=web, 2=pos, 3=atm | Request |
| 7 | `is_international` | int [0,1] | Transaction internationale | Calculé |
| 8 | `is_night` | int [0,1] | Heure 23h-5h | Calculé |
| 9 | `is_weekend` | int [0,1] | Samedi ou dimanche | Calculé |
| 10 | `amount_category` | int [0-3] | Catégorie de montant | Calculé |
| 11 | `distance_category` | int [0-3] | Distance IP ↔ marchand | Géoloc |
| 12 | `city_pop` | int | Population de la ville (IP) | Géoloc |

### Catégories de montant (v2)

Seuils ajustés pour contexte bancaire européen :

| Catégorie | Seuil v1 (ancien) | Seuil v2 (actuel) | Logique |
|-----------|-------------------|-------------------|---------|
| 0 | < 50€ | **< 100€** | Achats quotidiens (café, transport) |
| 1 | 50-200€ | **100-500€** | Achats courants (courses, resto) |
| 2 | 200-1000€ | **500-2000€** | Gros achats (électroménager) |
| 3 | > 1000€ | **> 2000€** | Achats exceptionnels |

**Pourquoi ce changement** : Les anciens seuils (hérités du dataset US) classifiaient 300€ comme "élevé", ce qui n'est pas adapté au contexte européen où les achats de 200-500€ sont courants.

### Importance des features

Résultats du training (gain-based importance) :

| Feature | Importance | % du total |
|---------|------------|------------|
| `amount_category` | 29,966,807 | **54%** |
| `trans_hour` | 8,483,786 | 15% |
| `is_night` | 6,364,611 | 11% |
| `amt` | 4,883,035 | 9% |
| `merchant_mcc` | 1,774,668 | 3% |
| `card_type` | 1,556,975 | 3% |
| `city_pop` | 726,886 | 1% |
| `trans_day` | 152,447 | 0.3% |
| `channel` | 8,966 | 0.02% |
| `distance_category` | 6,835 | 0.01% |
| `is_weekend` | 5,125 | 0.01% |
| `is_international` | 0 | 0% |

**Observations** :
- `amount_category` domine (54%) → Le montant est le signal principal de fraude
- `trans_hour` + `is_night` (26%) → Les fraudes ont des patterns temporels
- `distance_category` a peu d'impact (0.01%) → La géolocalisation IP n'est pas un signal fort dans ce dataset

### Seuils de décision

Dans le Decision Engine, le score ML est interprété :

| Score | Décision | Action |
|-------|----------|--------|
| < 0.50 | **ALLOW** | Transaction autorisée |
| 0.50 - 0.70 | **CHALLENGE** | Demande 2FA |
| > 0.70 | **DENY** | Transaction bloquée |

---

## 4. Alternatives Évaluées

### Choix du modèle

| Modèle | AUC | Latence | Taille | Verdict |
|--------|-----|---------|--------|---------|
| Logistic Regression | 0.88 | 1ms | 1 MB | ❌ Pas assez précis |
| Random Forest | 0.93 | 15ms | 500 MB | ❌ Trop lent |
| XGBoost | 0.95 | 8ms | 50 MB | ⚠️ Bon mais lourd |
| **LightGBM** ✅ | **0.996** | **5ms** | **350 KB** | ✅ **Choisi** |
| Neural Network | 0.94 | 20ms | 100 MB | ❌ Trop lent, black box |

**Justification LightGBM** :
- Meilleur AUC (0.996)
- Inférence ultra-rapide (<5ms)
- Modèle léger (350 KB)
- Interprétable (feature importance)

### Choix des features

| Feature évaluée | Incluse | Raison |
|-----------------|---------|--------|
| Montant brut (amt) | ✅ | Signal fort |
| Catégorie montant | ✅ | Réduit le bruit, améliore généralisation |
| Heure transaction | ✅ | Pattern temporel des fraudes |
| MCC marchand | ✅ | Certains secteurs plus risqués |
| Vélocité (tx/24h) | ❌ MVP | Nécessite Redis, complexité |
| Historique user | ❌ MVP | Nécessite DB, privacy concerns |
| Device fingerprint | ❌ MVP | Intégration complexe |

---

## 5. Limitations Connues & Action Requise

### ⚠️ PROBLÈME CRITIQUE : Biais du Dataset Kaggle

Le dataset Kaggle utilisé pour l'entraînement présente un **biais fondamental** qui rend le modèle **inadapté pour un usage en production bancaire européenne**.

#### Analyse du biais

| Catégorie de montant | Taux de fraude (Kaggle) | Taux réel (banque) | Écart |
|---------------------|-------------------------|--------------------| ------|
| < 100€ | 0.16% | ~0.1% | OK |
| 100-500€ | 1.0% | ~0.2% | **5x trop élevé** |
| 500-2000€ | **24.5%** | ~0.5% | **50x trop élevé** |
| > 2000€ | 0% | ~1% | Inversé |

**Conséquence** : Le modèle considère TOUT achat > 300€ comme frauduleux (score > 0.95).

#### Origine du problème

Le dataset Kaggle (kartik2112/fraud-detection) est :
- **Simulé** : Données générées, pas réelles
- **US-centré** : Patterns de consommation américains
- **Biaisé** : Fraudes artificiellement concentrées sur montants moyens-élevés
- **Médiane des fraudes = 396€** : Non représentatif d'une vraie distribution

#### Impact sur les prédictions

| Scénario | Score actuel | Score attendu (réel) | Verdict |
|----------|--------------|----------------------|---------|
| 25€ café | 0.001 | < 0.01 | ✅ OK |
| 45€ courses | 0.001 | < 0.01 | ✅ OK |
| **250€ Amazon FR** | **0.97** | < 0.1 | ❌ **FAUX POSITIF** |
| **500€ électroménager** | **0.98** | < 0.2 | ❌ **FAUX POSITIF** |
| 45€ IP russe | 0.001 | > 0.5 | ❌ **FAUX NÉGATIF** |

---

### 🔴 ACTION REQUISE : Changer de Dataset

**Le modèle actuel ne doit PAS être utilisé en production** sans l'une des actions suivantes :

#### Option 1 : Dataset IEEE-CIS Fraud Detection (Recommandé)

**Source** : [Kaggle IEEE-CIS](https://www.kaggle.com/c/ieee-fraud-detection)

| Caractéristique | Kaggle actuel | IEEE-CIS |
|-----------------|---------------|----------|
| Transactions | 1.3M | 590K train + 500K test |
| Origine | Simulé | **Verizon (réel)** |
| Features | 12 | **434 features** |
| Distribution | Biaisée | **Réaliste** |
| Montants | Concentrés | **Distribués** |

**Avantages** :
- Données réelles de e-commerce
- Distribution des fraudes réaliste
- Plus de features (device, browser, email domain)

**Inconvénients** :
- Plus complexe à preprocesser
- Nécessite feature selection

#### Option 2 : Dataset PaySim

**Source** : [Kaggle PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1)

| Caractéristique | Valeur |
|-----------------|--------|
| Transactions | 6.3M |
| Type | Mobile money (Afrique) |
| Fraudes | 8,213 (0.13%) |

**Avantages** :
- Grand volume
- Taux de fraude réaliste

**Inconvénients** :
- Mobile money ≠ carte bancaire
- Pas de features géographiques

#### Option 3 : Données Internes (Meilleure solution)

Si disponible, utiliser des données de transactions réelles (anonymisées) de la banque cible.

---

### Recommandations par priorité

| Priorité | Action | Effort | Impact |
|----------|--------|--------|--------|
| 🔴 **P0** | Changer pour IEEE-CIS | 2-3 jours | Élimine faux positifs montants |
| 🟡 P1 | Ajouter features vélocité | 1 jour | Détecte patterns temporels |
| 🟡 P2 | Intégrer détection VPN | 1 jour | Réduit faux négatifs géo |
| 🟢 P3 | SHAP explicabilité | 2 jours | Compliance audit |

---

## 6. Plan & Métriques

### Fichiers concernés

| Fichier | Description |
|---------|-------------|
| [scripts/train_fraud_model_kaggle.py](../scripts/train_fraud_model_kaggle.py) | Script d'entraînement |
| [artifacts/models/fraud_lgbm_kaggle.bin](../artifacts/models/fraud_lgbm_kaggle.bin) | Modèle binaire |
| [artifacts/models/fraud_model_metadata_kaggle.json](../artifacts/models/fraud_model_metadata_kaggle.json) | Métadonnées |
| [services/model-serving/app/main.py](../services/model-serving/app/main.py) | API FastAPI |
| [services/model-serving/app/inference.py](../services/model-serving/app/inference.py) | Module inférence |

### Métriques Prometheus

| Métrique | Description |
|----------|-------------|
| `http_request_latency_seconds` | Latence des prédictions |
| `http_requests_total` | Nombre de requêtes |
| `fraud_score_distribution` | Distribution des scores (à ajouter) |

### SLIs / SLOs

| Indicateur | Objectif | Alerte si |
|------------|----------|-----------|
| Latence P95 | < 30ms | > 50ms pendant 5min |
| Error rate | < 1% | > 2% pendant 2min |
| Model loaded | true | false pendant 1min |

### Évolutions prévues

| Phase | Feature | Impact | Status |
|-------|---------|--------|--------|
| **V1.1** | **Changer dataset → IEEE-CIS** | **Élimine faux positifs** | 🔴 **REQUIS** |
| V1.2 | Vélocité (tx/24h) | +5% AUC estimé | Planifié |
| V1.3 | Détection VPN | Réduire faux négatifs geo | Planifié |
| V2.0 | SHAP explainability | Compliance audit | Backlog |

---

## Annexes

### A. Entraînement du modèle

```bash
# Entraîner le modèle
python scripts/train_fraud_model_kaggle.py

# Output attendu
# ============================================================
# ✅ TRAINING COMPLETE!
# ============================================================
# AUC Score: 0.996090
# Model: artifacts/models/fraud_lgbm_kaggle.bin
# Features: 12
```

### B. Test de prédiction

```bash
# Transaction légitime (45€, IP FR)
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-001",
    "amount": 45.0,
    "merchant": {"mcc": "5411", "country": "FR"},
    "card": {"card_id": "c1", "user_id": "u1", "type": "physical"},
    "context": {"ip": "82.64.123.45", "channel": "pos"}
  }'

# Réponse attendue: score < 0.01
```

### C. Références

- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [Kaggle Dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection)
- [Scikit-learn Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html)

---

**Fin du Six-Pager ML Model**

Pour questions : virgile.ader@epitech.digital
