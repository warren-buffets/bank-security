# Métriques et KPI - FraudGuard

## Vue d'ensemble

Ce document définit les métriques clés pour évaluer et monitorer le système de détection de fraude FraudGuard. Ces métriques couvrent à la fois la **performance ML** et l'**impact business**.

---

## 📊 Métriques ML (Model Performance)

### 1. AUC-ROC (Area Under the Receiver Operating Characteristic Curve)

**Définition** : Mesure la capacité du modèle à distinguer entre transactions frauduleuses et légitimes, indépendamment du seuil de décision.

**Formule** :
```
AUC = ∫₀¹ TPR(FPR) d(FPR)
où TPR = True Positive Rate (Recall)
    FPR = False Positive Rate
```

**Interprétation** :
- **AUC = 1.0** : Modèle parfait (sépare complètement fraude/non-fraude)
- **AUC = 0.9-0.95** : Excellent
- **AUC = 0.8-0.9** : Bon
- **AUC = 0.7-0.8** : Acceptable
- **AUC < 0.7** : Médiocre
- **AUC = 0.5** : Équivalent à un tirage aléatoire

**Objectif FraudGuard** :
- ✅ **Minimum acceptable** : AUC ≥ 0.90
- 🎯 **Objectif** : AUC ≥ 0.94
- 🚀 **Excellence** : AUC ≥ 0.96

**Pourquoi c'est important** :
- Métrique standard de l'industrie pour comparer les modèles
- Indépendante du seuil de décision (threshold-agnostic)
- Reflète la qualité intrinsèque du scoring

**Monitoring** :
```python
# Calculer l'AUC en production
from sklearn.metrics import roc_auc_score

auc = roc_auc_score(y_true, y_pred_proba)

# Alerte si AUC < 0.90 (drift détecté)
if auc < 0.90:
    alert_model_degradation()
```

---

### 2. FPR (False Positive Rate) - Taux de Faux Positifs

**Définition** : Proportion de transactions légitimes incorrectement classées comme frauduleuses.

**Formule** :
```
FPR = FP / (FP + TN)
où FP = False Positives (vraies transactions bloquées)
    TN = True Negatives (vraies transactions autorisées)
```

**Interprétation** :
- **FPR = 0%** : Aucun faux positif (idéal mais irréaliste)
- **FPR = 1-2%** : Excellent (friction minimale)
- **FPR = 3-5%** : Acceptable
- **FPR > 5%** : Problématique (frustration client)

**Objectif FraudGuard** :
- 🎯 **Objectif** : FPR < 2%
- ⚠️ **Alerte** : FPR > 3%
- 🚨 **Critique** : FPR > 5%

**Impact Business** :
```
FPR de 2% sur 1M transactions/jour = 20,000 clients légitimes bloqués
→ Perte de revenus potentielle
→ Insatisfaction client
→ Appels au support
```

**Trade-off** : FPR vs TPR (True Positive Rate / Recall)
- Baisser le seuil → ↑ TPR (détecte plus de fraudes) mais ↑ FPR (plus de faux positifs)
- Augmenter le seuil → ↓ FPR (moins de faux positifs) mais ↓ TPR (manque des fraudes)

**Monitoring** :
```python
# Calculer FPR par segment
fpr_per_country = calculate_fpr_by_segment(transactions, 'country')

# Alerte si FPR d'un segment > 5%
for country, fpr in fpr_per_country.items():
    if fpr > 0.05:
        alert_high_fpr(country, fpr)
```

**Optimisation** :
- Ajuster le threshold par pays/segment
- Utiliser le mode **CHALLENGE** (2FA) au lieu de **DENY** pour les zones grises
- Implémenter un feedback loop (cas d'appels clients = faux positifs)

---

### 3. Calibration du Modèle

**Définition** : Mesure dans quelle mesure les scores prédits correspondent aux probabilités réelles.

**Objectif** : Un modèle bien calibré prédit 0.8 → 80% de chance réelle de fraude.

**Pourquoi c'est crucial** :
- Permet d'utiliser les scores comme **probabilités business**
- Essentiel pour fixer des seuils de décision rationnels
- Facilite l'interprétation pour les analystes

**Test de calibration** : Courbe de fiabilité (Reliability Diagram)

```
Bins de score   | % fraude prédit | % fraude réel | Calibration
----------------|-----------------|---------------|-------------
[0.0 - 0.1]    | 5%              | 4%            | ✅ Bon
[0.1 - 0.2]    | 15%             | 13%           | ✅ Bon
[0.2 - 0.3]    | 25%             | 27%           | ✅ Bon
[0.8 - 0.9]    | 85%             | 82%           | ✅ Bon
[0.9 - 1.0]    | 95%             | 93%           | ✅ Bon
```

**Métrique** : Brier Score
```
Brier Score = (1/N) Σ (p_i - y_i)²
où p_i = probabilité prédite
    y_i = vrai label (0 ou 1)

Brier Score parfait = 0
```

**Objectif FraudGuard** :
- 🎯 Brier Score < 0.10

**Méthodes de calibration** :

#### a) Platt Scaling (Regression Logistique)
```python
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

# Entraîner le modèle de base (LightGBM)
model = lgb.train(params, train_data)

# Calibrer avec Platt Scaling sur un validation set
calibrator = LogisticRegression()
calibrator.fit(val_scores.reshape(-1, 1), val_labels)

# Prédictions calibrées
calibrated_scores = calibrator.predict_proba(raw_scores.reshape(-1, 1))[:, 1]
```

**Avantages** :
- ✅ Simple et rapide
- ✅ Fonctionne bien pour les modèles non-calibrés

**Inconvénients** :
- ❌ Assume une transformation sigmoïde
- ❌ Peut sous-performer pour les distributions non-linéaires

#### b) Isotonic Regression (Non-paramétrique)
```python
from sklearn.isotonic import IsotonicRegression

# Calibrer avec Isotonic Regression
calibrator = IsotonicRegression(out_of_bounds='clip')
calibrator.fit(val_scores, val_labels)

# Prédictions calibrées
calibrated_scores = calibrator.predict(raw_scores)
```

**Avantages** :
- ✅ Plus flexible (non-paramétrique)
- ✅ Meilleur pour les distributions complexes

**Inconvénients** :
- ❌ Risque d'overfitting sur petits datasets
- ❌ Plus lent

**Notre choix recommandé** : **Platt Scaling** pour démarrer, puis **Isotonic Regression** si Brier Score > 0.10

**Intégration dans le pipeline** :
```python
# 1. Entraîner le modèle principal
model = train_lightgbm(train_data)

# 2. Calibrer sur validation set
calibrator = train_calibrator(model, val_data)

# 3. Sauvegarder les deux
save_model(model, "gbdt_v1.bin")
save_calibrator(calibrator, "calibrator_v1.pkl")

# 4. En production
raw_score = model.predict(features)
calibrated_prob = calibrator.predict(raw_score)
```

**Monitoring** :
```python
# Vérifier la calibration en production chaque semaine
def check_calibration(predictions, labels):
    bins = np.linspace(0, 1, 11)
    for i in range(len(bins) - 1):
        mask = (predictions >= bins[i]) & (predictions < bins[i+1])
        pred_mean = predictions[mask].mean()
        true_mean = labels[mask].mean()

        if abs(pred_mean - true_mean) > 0.10:  # Décalibration > 10%
            alert_calibration_drift(bins[i], pred_mean, true_mean)
```

---

## 💼 Métriques Business

### 4. Precision (Précision)

**Définition** : Proportion de vraies fraudes parmi les transactions bloquées.

**Formule** :
```
Precision = TP / (TP + FP)
```

**Interprétation** :
- Precision = 90% → 9 transactions bloquées sur 10 sont de vraies fraudes

**Objectif** : Precision ≥ 75%

---

### 5. Recall (Taux de détection)

**Définition** : Proportion de fraudes réellement détectées.

**Formule** :
```
Recall = TP / (TP + FN)
```

**Objectif** : Recall ≥ 94%

---

### 6. F1-Score

**Définition** : Moyenne harmonique de Precision et Recall.

**Formule** :
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**Objectif** : F1 ≥ 0.85

---

## ⚡ Métriques Opérationnelles

### 7. Latence (P95, P99)

- **P95 < 100ms** : 95% des requêtes répondent en moins de 100ms
- **P99 < 200ms** : 99% des requêtes répondent en moins de 200ms

### 8. Throughput

- **10,000 TPS** (transactions par seconde) en conditions normales
- **50,000 TPS** en pic

### 9. Disponibilité

- **SLA : 99.95%** (< 4.38 heures de downtime/an)

---

## 📈 Dashboard de Monitoring

### Métriques à tracker en temps réel

```yaml
ML Metrics:
  - AUC-ROC (rolling 7 days)
  - FPR par pays/segment
  - Calibration (Brier Score)
  - Drift detection (KL divergence)

Business Metrics:
  - Montant de fraude bloqué (€)
  - Montant de faux positifs (€)
  - Taux de contestation (chargeback rate)
  - ROI du système

Operational Metrics:
  - P95/P99 latency
  - Throughput (TPS)
  - Error rate
  - Redis/Kafka health
```

---

## 🎯 Résumé des Objectifs

| Métrique | Objectif | Alerte | Critique |
|----------|----------|--------|----------|
| **AUC-ROC** | ≥ 0.94 | < 0.92 | < 0.90 |
| **FPR** | < 2% | > 3% | > 5% |
| **Brier Score** | < 0.10 | > 0.12 | > 0.15 |
| **Precision** | ≥ 75% | < 70% | < 65% |
| **Recall** | ≥ 94% | < 92% | < 90% |
| **P95 Latency** | < 100ms | > 120ms | > 150ms |

---

## 📚 Références

- [Scikit-learn: Probability Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Google: Rules of Machine Learning - Rule #36 (Calibration)](https://developers.google.com/machine-learning/guides/rules-of-ml)
- [Stripe: Online Payments Fraud Detection](https://stripe.com/docs/disputes)
