# ML Fraud Detection Model - Six-Pager Technique

**Version** : 3.0
**Date** : Janvier 2026
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

**Modèle LightGBM** entraîné sur le dataset **IEEE-CIS Fraud Detection** (590K transactions Vesta) :

1. **12 features** : montant, heure, MCC, type de carte, distance géo, population urbaine
2. **Gradient Boosting** : LightGBM pour rapidité d'inférence (<10ms)
3. **Distribution réaliste** : Taux de fraude équilibré (~3.5%)

### Résultats (v3 - IEEE-CIS)

| Métrique | Valeur v2 (Kaggle) | Valeur v3 (IEEE-CIS) | Objectif |
|----------|-------------------|---------------------|----------|
| **AUC-ROC** | 0.996 (biaisé) | **0.823** | > 0.80 ✅ |
| **Recall (Fraudes)** | 97% (biaisé) | **82%** | > 80% ✅ |
| **Precision (Fraudes)** | 16% | **20%** | > 10% ✅ |
| **Latence inférence** | < 5ms | **< 5ms** | < 30ms ✅ |

### Portée

**Implémenté (v3)** :
- ✅ Dataset IEEE-CIS (données réelles Vesta)
- ✅ Distribution de fraudes réaliste (3.5% global)
- ✅ 12 features incluant géolocalisation IP
- ✅ Intégration dans model-serving (FastAPI)

**Hors scope MVP** :
- ❌ Features de vélocité (transactions/24h)
- ❌ Détection de drift automatique
- ❌ Explicabilité SHAP

---

## 2. Contexte & Principes

### Dataset d'entraînement (v3)

**Source** : [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) (Vesta Corporation)

| Caractéristique | Valeur |
|-----------------|--------|
| Transactions totales | 590,540 |
| Transactions frauduleuses | 20,663 (**3.5%**) |
| Période | Réel (e-commerce) |
| Origine | Données Vesta Corporation |

### Distribution des fraudes (v3 - Équilibrée)

| Catégorie de montant | Fraudes | Total | Taux |
|---------------------|---------|-------|------|
| < 100€ | 2,519 | 73,666 | **3.42%** |
| 100-500€ | 1,398 | 39,834 | **3.51%** |
| 500-2000€ | 203 | 4,206 | **4.83%** |
| > 2000€ | 15 | 402 | **3.73%** |

**Amélioration clé** : La distribution est maintenant réaliste et équilibrée. Plus de biais vers les gros montants.

### Comparaison des datasets

| Aspect | Kaggle v2 (ancien) | IEEE-CIS v3 (actuel) |
|--------|-------------------|---------------------|
| Source | Simulé | **Données réelles** |
| Fraude 500-2000€ | 24.5% (biaisé!) | **4.83%** (réaliste) |
| Distribution | Concentrée | **Équilibrée** |
| AUC | 0.996 (overfit) | **0.823** (généralisable) |

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
│                    Model Serving (Port 8001)                │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                Feature Engineering                   │   │
│  │                                                      │   │
│  │  Transaction ──► [amt, hour, day, mcc, card_type,    │   │
│  │                   channel, is_intl, is_night,        │   │
│  │                   is_weekend, amt_cat, dist_cat,     │   │
│  │                   city_pop]                          │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LightGBM Model (GBDT)                   │   │
│  │                                                      │   │
│  │  - 200 boosting rounds                               │   │
│  │  - 64 leaves per tree                                │   │
│  │  - scale_pos_weight: 27.58 (class imbalance)         │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
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

### Catégories de montant

| Catégorie | Seuil | Logique |
|-----------|-------|---------|
| 0 | < 100€ | Achats quotidiens (café, transport) |
| 1 | 100-500€ | Achats courants (courses, resto) |
| 2 | 500-2000€ | Gros achats (électroménager) |
| 3 | > 2000€ | Achats exceptionnels |

### Importance des features (v3 - IEEE-CIS)

| Feature | Importance | % du total |
|---------|------------|------------|
| `amount` | 394,475 | **36%** |
| `city_pop` | 251,012 | **23%** |
| `card_type` | 109,276 | 10% |
| `merchant_mcc` | 86,834 | 8% |
| `channel` | 79,794 | 7% |
| `trans_hour` | 73,186 | 7% |
| `is_international` | 36,035 | 3% |
| `trans_day` | 29,971 | 3% |
| `distance_category` | 14,213 | 1% |
| `amount_category` | 10,199 | 1% |
| `is_night` | 3,157 | 0.3% |
| `is_weekend` | 768 | 0.1% |

**Observations (v3)** :
- `amount` est le signal principal (36%) - direct et non biaisé
- `city_pop` (23%) - La géolocalisation IP a maintenant un vrai impact
- `amount_category` (1%) - N'est plus le facteur dominant (vs 54% avant)

### Seuils de décision

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
| Logistic Regression | 0.75 | 1ms | 1 MB | ❌ Pas assez précis |
| Random Forest | 0.80 | 15ms | 500 MB | ❌ Trop lent |
| XGBoost | 0.82 | 8ms | 50 MB | ⚠️ Bon mais lourd |
| **LightGBM** ✅ | **0.823** | **5ms** | **350 KB** | ✅ **Choisi** |
| Neural Network | 0.81 | 20ms | 100 MB | ❌ Trop lent, black box |

### Choix des features

| Feature évaluée | Incluse | Raison |
|-----------------|---------|--------|
| Montant brut (amt) | ✅ | Signal fort |
| Catégorie montant | ✅ | Réduit le bruit |
| Heure transaction | ✅ | Pattern temporel |
| MCC marchand | ✅ | Certains secteurs risqués |
| Population ville (IP) | ✅ | **Nouveau signal fort** |
| Vélocité (tx/24h) | ❌ MVP | Nécessite Redis, complexité |

### Choix du dataset

| Dataset | Verdict | Raison |
|---------|---------|--------|
| Kaggle kartik2112 | ❌ | Données simulées, biais montants |
| **IEEE-CIS** ✅ | ✅ | Données réelles Vesta, distribution équilibrée |
| PaySim | ⚠️ | Mobile money ≠ carte bancaire |

---

## 5. Historique des versions

### v3.0 (Janvier 2026) - IEEE-CIS Dataset

**Changement majeur** : Migration vers le dataset IEEE-CIS pour corriger le biais.

| Aspect | v2 (Kaggle) | v3 (IEEE-CIS) | Amélioration |
|--------|-------------|---------------|--------------|
| Fraude 500€ | Score 0.97 | Score 0.53 | ✅ Réaliste |
| Fraude 250€ | Score 0.80 | Score 0.65 | ✅ Moins de faux positifs |
| Dataset | Simulé | Réel | ✅ Production ready |
| AUC | 0.996 (overfit) | 0.823 | ✅ Généralisable |

### v2.0 (Décembre 2025) - Ajustement seuils

- Changement des seuils de montant (50/200/1000 → 100/500/2000)
- Ajout géolocalisation IP (ip-api.com)
- Cache Redis pour les IP

### v1.0 (Novembre 2025) - MVP Initial

- Premier modèle LightGBM
- 10 features de base
- Dataset Kaggle

---

## 6. Plan & Métriques

### Fichiers concernés

| Fichier | Description |
|---------|-------------|
| [scripts/train_fraud_model_ieee.py](../scripts/train_fraud_model_ieee.py) | Script d'entraînement IEEE-CIS |
| [artifacts/models/fraud_lgbm_kaggle.bin](../artifacts/models/fraud_lgbm_kaggle.bin) | Modèle binaire (compatible API) |
| [artifacts/models/fraud_model_metadata_ieee.json](../artifacts/models/fraud_model_metadata_ieee.json) | Métadonnées |
| [services/model-serving/app/main.py](../services/model-serving/app/main.py) | API FastAPI |
| [services/model-serving/app/geolocation.py](../services/model-serving/app/geolocation.py) | Module géolocalisation IP |

### Métriques Prometheus

| Métrique | Description |
|----------|-------------|
| `http_request_latency_seconds` | Latence des prédictions |
| `geolocation_cache_hits_total` | Hits cache géolocalisation |
| `geolocation_api_latency_seconds` | Latence API ip-api.com |
| `geolocation_country_requests_total` | Distribution par pays |

### SLIs / SLOs

| Indicateur | Objectif | Alerte si |
|------------|----------|-----------|
| Latence P95 | < 30ms | > 50ms pendant 5min |
| Error rate | < 1% | > 2% pendant 2min |
| Model loaded | true | false pendant 1min |
| Geo cache hit rate | > 80% | < 60% pendant 10min |

### Évolutions prévues

| Phase | Feature | Impact | Status |
|-------|---------|--------|--------|
| **V3.0** | **Dataset IEEE-CIS** | **Corrige biais** | ✅ **FAIT** |
| V3.1 | Vélocité (tx/24h) | +5% AUC estimé | Planifié |
| V3.2 | Détection VPN | Réduire faux négatifs geo | Planifié |
| V4.0 | SHAP explicabilité | Compliance audit | Backlog |

---

## Annexes

### A. Entraînement du modèle

```bash
# Télécharger le dataset IEEE-CIS
kaggle competitions download -c ieee-fraud-detection -p artifacts/data/ --unzip

# Entraîner le modèle
python scripts/train_fraud_model_ieee.py

# Output attendu
# ============================================================
# ✅ TRAINING COMPLETE!
# ============================================================
# Base Model AUC: 0.823109
# Model: artifacts/models/fraud_lgbm_kaggle.bin
# Features: 12
```

### B. Test de prédiction

```bash
# Transaction normale 250€ (ne doit PAS être considérée comme fraude)
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-001",
    "amount": 250.0,
    "merchant": {"mcc": "5411", "country": "FR"},
    "card": {"card_id": "c1", "user_id": "u1", "type": "physical"},
    "context": {"ip": "89.225.140.45", "channel": "pos"}
  }'

# Réponse attendue: score ~0.50-0.65 (CHALLENGE, pas DENY)
```

### C. Références

- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection)
- [Vesta Corporation](https://trustvesta.com/)

---

**Fin du Six-Pager ML Model v3**

Pour questions : virgile.ader@epitech.digital
