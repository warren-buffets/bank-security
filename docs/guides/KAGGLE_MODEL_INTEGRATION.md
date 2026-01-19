# Intégration du modèle Kaggle LightGBM

Guide pour intégrer le modèle de détection de fraude depuis :
https://www.kaggle.com/code/barkataliarbab/mercor-fraud-detection-using-lightgbm

## 📋 Prérequis

1. Compte Kaggle
2. Accès au dataset de fraude
3. Python avec LightGBM installé

---

## 🎯 Étape 1 : Entraîner le modèle

### 1.1 Télécharge le notebook Kaggle

```bash
# Installe l'API Kaggle
pip install kaggle

# Configure tes credentials Kaggle
# (Télécharge kaggle.json depuis ton compte Kaggle)
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

### 1.2 Entraîne le modèle

Crée un script Python pour entraîner :

```python
# train_fraud_model.py
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

# Charge le dataset de fraude
# Remplace par le vrai dataset Kaggle
df = pd.read_csv('fraud_dataset.csv')

# Features utilisées dans le notebook Kaggle
feature_cols = [
    'amt',                    # Transaction amount
    'city_pop',              # City population
    'merchant_lat',          # Merchant latitude
    'merchant_long',         # Merchant longitude
    'age',                   # Cardholder age
    'trans_hour',            # Transaction hour
    'trans_day',             # Day of week
    'merchant_category',     # Merchant category (MCC)
    'distance_from_home',    # Distance from home
    '# ... autres features du notebook
]

X = df[feature_cols]
y = df['is_fraud']  # 0 = légit, 1 = fraude

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Entraîne LightGBM (paramètres du notebook)
params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': 0
}

train_data = lgb.Dataset(X_train, label=y_train)
valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[valid_data],
    callbacks=[lgb.early_stopping(stopping_rounds=50)]
)

# Évalue
y_pred = model.predict(X_test)
auc = roc_auc_score(y_test, y_pred)
print(f"AUC Score: {auc:.4f}")

# Sauvegarde le modèle
model.save_model('fraud_lgbm_model.bin')
print("✓ Modèle sauvegardé : fraud_lgbm_model.bin")

# Sauvegarde aussi la liste des features
import json
with open('feature_names.json', 'w') as f:
    json.dump(feature_cols, f)
print("✓ Features sauvegardées : feature_names.json")
```

---

## 🔧 Étape 2 : Intégrer au projet

### 2.1 Copie le modèle

```bash
# Depuis le dossier où tu as entraîné
cp fraud_lgbm_model.bin /path/to/bank-security/artifacts/models/
```

### 2.2 Met à jour config.py

```python
# services/model-serving/app/config.py

expected_features: list = [
    # REMPLACE avec les features du notebook Kaggle
    "amt",
    "city_pop",
    "merchant_lat",
    "merchant_long",
    "age",
    "trans_hour",
    "trans_day",
    "merchant_category",
    "distance_from_home",
    # ... toutes les features
]
```

### 2.3 Adapte main.py pour extraire les features

```python
# services/model-serving/app/main.py

@app.post("/predict")
async def predict(request: PredictRequest):
    """Predict fraud probability."""
    
    # Extrait les features depuis la requête
    features = extract_features(request)
    
    # Prédiction
    score = model_inference.predict(features)
    
    return {
        "event_id": request.event_id,
        "score": score,
        "model_version": "fraud_lgbm_v1"
    }

def extract_features(request: PredictRequest) -> List[float]:
    """Extract features matching Kaggle model."""
    
    # MAP les champs de ta requête aux features du modèle
    features = [
        request.amount,                          # amt
        0.0,                                     # city_pop (à calculer)
        float(request.merchant.get('lat', 0)),  # merchant_lat
        float(request.merchant.get('long', 0)), # merchant_long
        0.0,                                     # age (à calculer)
        datetime.now().hour,                     # trans_hour
        datetime.now().weekday(),                # trans_day
        int(request.merchant.get('mcc', 0)),    # merchant_category
        0.0,                                     # distance_from_home (à calculer)
        # ... autres features
    ]
    
    return features
```

---

## 🎨 Étape 3 : Features manquantes

Certaines features du modèle Kaggle ne sont pas disponibles dans ta requête API.
Tu as 2 options :

### Option A : Calcul en temps réel (Feature Store)

```python
# Récupère depuis Redis/PostgreSQL
city_pop = await feature_store.get_city_population(request.context.geo)
user_age = await feature_store.get_user_age(request.card.user_id)
distance = calculate_distance(user_home, merchant_location)
```

### Option B : Valeurs par défaut

```python
# Utilise des valeurs moyennes/neutres
city_pop = 100000  # Moyenne
age = 35           # Moyenne
distance = 10.0    # Moyenne
```

**Recommandation** : Commence avec Option B, puis implémente le Feature Store.

---

## 🧪 Étape 4 : Test

### 4.1 Update docker-compose.yml

```yaml
model-serving:
  environment:
    - MODEL_SERVING_MODEL_PATH=/app/artifacts/models/fraud_lgbm_model.bin
```

### 4.2 Redémarre

```bash
docker compose restart model-serving decision-engine
```

### 4.3 Teste

```bash
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test_kaggle_model",
    "tenant_id": "bank-001",
    "amount": 850.00,
    "currency": "EUR",
    "merchant": {
      "id": "m789",
      "mcc": "5812",
      "country": "FR",
      "lat": "48.8566",
      "long": "2.3522"
    },
    "card": {"card_id": "c456", "type": "physical", "user_id": "u789"},
    "context": {"ip": "5.6.7.8", "geo": "FR", "device_id": "d456", "channel": "app"}
  }'
```

Devrait retourner un score entre 0 et 1.

---

## 📊 Étape 5 : Monitoring

Vérifie que le modèle fonctionne :

```bash
# Logs
docker logs antifraud-model-serving

# Métriques Prometheus
curl http://localhost:8001/metrics | grep model_predictions
```

---

## ⚠️ Points d'attention

1. **Feature alignment** : Les features doivent être dans le MÊME ordre qu'à l'entraînement
2. **Normalisation** : Si le modèle a été entraîné sur des données normalisées, applique la même normalisation
3. **Features manquantes** : Gère les valeurs nulles avec des defaults sensés
4. **Performance** : LightGBM est rapide mais vérifie la latence (<30ms)

---

## 🎯 Prochaines étapes

1. ✅ Entraîne le modèle Kaggle
2. ✅ Intègre dans Model Serving
3. ✅ Teste l'API
4. 🔄 Implémente le Feature Store pour features temps réel
5. 🔄 Ajoute le monitoring des prédictions
6. 🔄 Configure des alertes si score distribution change (drift)

