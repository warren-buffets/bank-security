"""
Train fraud detection model using Kaggle dataset
Real transaction data with 1.2M+ transactions
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from datetime import datetime
import json

print("=" * 60)
print("FRAUD DETECTION MODEL - KAGGLE DATASET TRAINING")
print("=" * 60)

# ============================================================================
# 1. Load Kaggle dataset
# ============================================================================
print("\n📊 Loading Kaggle fraud detection dataset...")

df = pd.read_csv('artifacts/data/fraudTrain.csv')
print(f"✓ Loaded {len(df):,} transactions")
print(f"✓ Columns: {list(df.columns)}")
print(f"\n✓ Fraud rate: {df['is_fraud'].mean()*100:.4f}%")
print(f"✓ Fraud transactions: {df['is_fraud'].sum():,}")
print(f"✓ Legit transactions: {(~df['is_fraud'].astype(bool)).sum():,}")

# ============================================================================
# 2. Feature engineering
# ============================================================================
print("\n🔧 Engineering features...")

# Convert datetime
df['trans_datetime'] = pd.to_datetime(df['trans_date_trans_time'])
df['trans_hour'] = df['trans_datetime'].dt.hour
df['trans_day'] = df['trans_datetime'].dt.dayofweek

# Merchant category mapping (simplified MCCs)
category_to_mcc = {
    'gas_transport': 5541,  # Gas stations
    'grocery_pos': 5411,    # Grocery stores
    'food_dining': 5812,    # Restaurants
    'shopping_net': 5999,   # Misc retail
    'shopping_pos': 5999,   # Misc retail
    'entertainment': 7832,  # Movies
    'personal_care': 7298,  # Health/beauty
    'health_fitness': 7298, # Health
    'travel': 4511,         # Airlines
    'kids_pets': 5999,      # Misc
    'home': 5211,           # Building materials
    'misc_net': 5999,       # Misc online
    'misc_pos': 5999,       # Misc POS
    'grocery_net': 5411     # Grocery online
}
df['merchant_mcc'] = df['category'].map(category_to_mcc).fillna(5999).astype(int)

# Card type (assume physical for POS, virtual for net)
df['card_type'] = df['category'].str.contains('net').astype(int)  # 0=physical, 1=virtual

# Channel (0=app, 1=web, 2=pos, 3=atm)
df['channel'] = 2  # Most are POS
df.loc[df['category'].str.contains('net'), 'channel'] = 1  # Web

# International (check if state is valid US state)
df['is_international'] = 0  # All US in this dataset

# Derived features
df['is_night'] = ((df['trans_hour'] >= 23) | (df['trans_hour'] <= 5)).astype(int)
df['is_weekend'] = (df['trans_day'] >= 5).astype(int)
df['amount_category'] = pd.cut(df['amt'], bins=[0, 50, 200, 1000, np.inf], labels=[0, 1, 2, 3]).astype(int)

# Distance between user and merchant (fraud indicator)
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km"""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

df['distance_km'] = haversine_distance(df['lat'], df['long'], df['merch_lat'], df['merch_long'])
df['distance_category'] = pd.cut(df['distance_km'], bins=[0, 10, 50, 200, np.inf], labels=[0, 1, 2, 3]).astype(int)

print(f"✓ Features engineered")

# ============================================================================
# 3. Prepare training data
# ============================================================================
print("\n🎯 Preparing training data...")

feature_cols = [
    'amt',                  # amount
    'trans_hour',
    'trans_day',
    'merchant_mcc',
    'card_type',
    'channel',
    'is_international',
    'is_night',
    'is_weekend',
    'amount_category',
    'distance_category',    # New: distance from home
    'city_pop'              # New: city population (fraud indicator)
]

# Rename amt to amount for consistency
df['amount'] = df['amt']

X = df[feature_cols]
y = df['is_fraud']

# Handle missing values
X = X.fillna(0)

print(f"✓ Features selected: {len(feature_cols)}")
print(f"✓ Training samples: {len(X):,}")

# ============================================================================
# 4. Train/test split
# ============================================================================
print("\n📊 Splitting data...")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"✓ Train set: {len(X_train):,} samples ({y_train.sum():,} fraud)")
print(f"✓ Test set: {len(X_test):,} samples ({y_test.sum():,} fraud)")

# ============================================================================
# 5. Train LightGBM model
# ============================================================================
print("\n🚀 Training LightGBM model...")

# Calculate scale_pos_weight for imbalanced dataset
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"✓ Class imbalance ratio: {scale_pos_weight:.2f}")

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'scale_pos_weight': scale_pos_weight,
    'verbose': -1
}

train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=100,
    valid_sets=[test_data],
    callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(period=10)]
)

print(f"✓ Model trained with {model.best_iteration} iterations")

# ============================================================================
# 6. Evaluate model
# ============================================================================
print("\n📈 Evaluating model...")

y_pred_proba = model.predict(X_test)
y_pred = (y_pred_proba > 0.5).astype(int)

auc_score = roc_auc_score(y_test, y_pred_proba)
print(f"\n✓ AUC Score: {auc_score:.6f}")

print("\n" + "=" * 60)
print("CLASSIFICATION REPORT")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))

print("\n" + "=" * 60)
print("CONFUSION MATRIX")
print("=" * 60)
cm = confusion_matrix(y_test, y_pred)
print(f"True Negatives:  {cm[0][0]:,}")
print(f"False Positives: {cm[0][1]:,}")
print(f"False Negatives: {cm[1][0]:,}")
print(f"True Positives:  {cm[1][1]:,}")

# ============================================================================
# 7. Feature importance
# ============================================================================
print("\n" + "=" * 60)
print("FEATURE IMPORTANCE")
print("=" * 60)

importance = model.feature_importance(importance_type='gain')
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': importance
}).sort_values('importance', ascending=False)

print(feature_importance.to_string(index=False))

# ============================================================================
# 8. Save model
# ============================================================================
print("\n💾 Saving model...")

model.save_model('artifacts/models/fraud_lgbm_kaggle.bin')
print(f"✓ Model saved to artifacts/models/fraud_lgbm_kaggle.bin")

# Save metadata
metadata = {
    'model_version': 'fraud_lgbm_kaggle_v1',
    'trained_at': datetime.now().isoformat(),
    'dataset': 'kaggle_kartik2112',
    'n_samples': len(df),
    'n_train': len(X_train),
    'n_test': len(X_test),
    'fraud_rate': float(y.mean()),
    'auc_score': float(auc_score),
    'feature_names': feature_cols,
    'feature_importance': [
        {'feature': row['feature'], 'importance': float(row['importance'])}
        for _, row in feature_importance.iterrows()
    ]
}

with open('artifacts/models/fraud_model_metadata_kaggle.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"✓ Metadata saved to artifacts/models/fraud_model_metadata_kaggle.json")

print("\n" + "=" * 60)
print("✅ TRAINING COMPLETE!")
print("=" * 60)
print(f"AUC Score: {auc_score:.6f}")
print(f"Model: artifacts/models/fraud_lgbm_kaggle.bin")
print(f"Features: {len(feature_cols)}")
