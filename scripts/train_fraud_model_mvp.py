"""
Train a simplified fraud detection model for MVP
Using only features available in the current API
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import json

print("=" * 60)
print("FRAUD DETECTION MODEL - MVP TRAINING")
print("=" * 60)

# ============================================================================
# 1. Generate synthetic fraud dataset
# ============================================================================
print("\n📊 Generating synthetic fraud dataset...")

np.random.seed(42)
n_samples = 50000
fraud_rate = 0.02  # 2% fraud

# Features available in current API
data = {
    # Transaction features
    'amount': np.random.lognormal(4, 2, n_samples),  # Log-normal distribution
    'trans_hour': np.random.randint(0, 24, n_samples),
    'trans_day': np.random.randint(0, 7, n_samples),
    
    # Merchant features
    'merchant_mcc': np.random.choice([5411, 5812, 5999, 7995, 6011], n_samples),
    'merchant_country': np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),  # 0=FR, 1=international
    
    # Card features
    'card_type': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),  # 0=physical, 1=virtual
    
    # Context features  
    'channel': np.random.choice([0, 1, 2, 3], n_samples),  # 0=app, 1=web, 2=pos, 3=atm
    'is_international': np.random.choice([0, 1], n_samples, p=[0.85, 0.15]),
    
    # Derived features (using defaults for MVP)
    'is_night': np.zeros(n_samples),  # Will calculate from trans_hour
    'is_weekend': np.zeros(n_samples),  # Will calculate from trans_day
    'amount_category': np.zeros(n_samples),  # Will calculate from amount
}

df = pd.DataFrame(data)

# Calculate derived features
df['is_night'] = ((df['trans_hour'] >= 23) | (df['trans_hour'] <= 5)).astype(int)
df['is_weekend'] = (df['trans_day'] >= 5).astype(int)
df['amount_category'] = pd.cut(df['amount'], bins=[0, 50, 200, 1000, np.inf], labels=[0, 1, 2, 3]).astype(int)

# ============================================================================
# 2. Generate fraud labels with realistic patterns
# ============================================================================
print("🎯 Generating fraud labels with realistic patterns...")

# Fraud probability increases with:
fraud_score = (
    (df['amount'] > 500).astype(int) * 0.3 +           # High amount
    (df['is_night']).astype(int) * 0.2 +               # Night transactions
    (df['merchant_mcc'] == 7995).astype(int) * 0.3 +   # Gambling
    (df['is_international']).astype(int) * 0.2 +       # International
    (df['card_type'] == 1).astype(int) * 0.1 +         # Virtual card
    np.random.random(n_samples) * 0.3                  # Random noise
)

# Convert to binary with threshold
fraud_threshold = np.percentile(fraud_score, 100 * (1 - fraud_rate))
df['is_fraud'] = (fraud_score > fraud_threshold).astype(int)

print(f"✓ Dataset created: {len(df)} transactions")
print(f"✓ Fraud rate: {df['is_fraud'].mean()*100:.2f}%")
print(f"✓ Fraud transactions: {df['is_fraud'].sum()}")
print(f"✓ Legit transactions: {(1-df['is_fraud']).sum()}")

# ============================================================================
# 3. Prepare training data
# ============================================================================
print("\n🔧 Preparing training data...")

feature_cols = [
    'amount',
    'trans_hour',
    'trans_day',
    'merchant_mcc',
    'merchant_country',
    'card_type',
    'channel',
    'is_international',
    'is_night',
    'is_weekend',
    'amount_category'
]

X = df[feature_cols]
y = df['is_fraud']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"✓ Train set: {len(X_train)} samples ({y_train.sum()} fraud)")
print(f"✓ Test set: {len(X_test)} samples ({y_test.sum()} fraud)")

# ============================================================================
# 4. Train LightGBM model
# ============================================================================
print("\n🤖 Training LightGBM model...")

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'seed': 42
}

train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_cols)
valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data, feature_name=feature_cols)

model = lgb.train(
    params,
    train_data,
    num_boost_round=500,
    valid_sets=[train_data, valid_data],
    valid_names=['train', 'valid'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.log_evaluation(period=50)
    ]
)

print(f"✓ Model trained with {model.best_iteration} iterations")

# ============================================================================
# 5. Evaluate model
# ============================================================================
print("\n📈 Evaluating model...")

y_pred_proba = model.predict(X_test)
y_pred = (y_pred_proba > 0.5).astype(int)

auc = roc_auc_score(y_test, y_pred_proba)
print(f"\n✓ AUC Score: {auc:.4f}")

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(cm)

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))

# Feature importance
print("\n🎯 Feature Importance:")
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importance(importance_type='gain')
}).sort_values('importance', ascending=False)
print(feature_importance.to_string(index=False))

# ============================================================================
# 6. Save model and metadata
# ============================================================================
print("\n💾 Saving model...")

model_path = 'artifacts/models/fraud_lgbm_mvp.bin'
model.save_model(model_path)
print(f"✓ Model saved: {model_path}")

# Save feature metadata
metadata = {
    'feature_names': feature_cols,
    'model_version': 'fraud_lgbm_mvp_v1',
    'auc_score': float(auc),
    'training_date': pd.Timestamp.now().isoformat(),
    'num_iterations': model.best_iteration,
    'fraud_rate': float(df['is_fraud'].mean()),
    'feature_importance': feature_importance.to_dict('records')
}

metadata_path = 'artifacts/models/fraud_model_metadata.json'
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)
print(f"✓ Metadata saved: {metadata_path}")

print("\n" + "=" * 60)
print("✅ MODEL TRAINING COMPLETE!")
print("=" * 60)
print(f"\n📌 Next steps:")
print(f"1. Update docker-compose.yml: MODEL_SERVING_MODEL_PATH=/app/artifacts/models/fraud_lgbm_mvp.bin")
print(f"2. Update services/model-serving/app/config.py with feature_names from metadata")
print(f"3. Update services/model-serving/app/main.py to extract features")
print(f"4. Restart services: docker compose restart model-serving decision-engine")
