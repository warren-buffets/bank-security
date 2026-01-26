"""
Train fraud detection model using IEEE-CIS Fraud Detection dataset
Real Vesta payment transaction data (590K+ transactions)
More balanced fraud distribution than Kaggle kartik2112

Includes temperature scaling calibration for better score separation.
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from datetime import datetime
import json
import gc
import pickle

print("=" * 60)
print("FRAUD DETECTION MODEL - IEEE-CIS DATASET TRAINING")
print("=" * 60)

# ============================================================================
# 1. Load IEEE-CIS dataset
# ============================================================================
print("\n📊 Loading IEEE-CIS fraud detection dataset...")

# Load transaction data
df_trans = pd.read_csv('artifacts/data/train_transaction.csv')
print(f"✓ Loaded {len(df_trans):,} transactions")
print(f"✓ Transaction columns: {len(df_trans.columns)}")

# Load identity data (optional enrichment)
df_id = pd.read_csv('artifacts/data/train_identity.csv')
print(f"✓ Loaded {len(df_id):,} identity records")

# Merge on TransactionID
df = df_trans.merge(df_id, on='TransactionID', how='left')
print(f"✓ Merged dataset: {len(df):,} transactions")

# Clean up memory
del df_trans, df_id
gc.collect()

print(f"\n✓ Fraud rate: {df['isFraud'].mean()*100:.4f}%")
print(f"✓ Fraud transactions: {df['isFraud'].sum():,}")
print(f"✓ Legit transactions: {(~df['isFraud'].astype(bool)).sum():,}")

# ============================================================================
# 2. Feature engineering
# ============================================================================
print("\n🔧 Engineering features...")

# TransactionDT is seconds from a reference time
# Convert to hour of day and day of week
df['trans_hour'] = (df['TransactionDT'] // 3600) % 24
df['trans_day'] = (df['TransactionDT'] // 86400) % 7

# Amount (already in TransactionAmt)
df['amount'] = df['TransactionAmt']

# Amount category (aligned with our existing model)
df['amount_category'] = pd.cut(
    df['amount'],
    bins=[0, 100, 500, 2000, np.inf],
    labels=[0, 1, 2, 3]
).astype(float).fillna(1).astype(int)

# Product code as MCC proxy
# ProductCD: W, H, C, S, R
product_to_mcc = {
    'W': 5999,   # Misc retail (most common)
    'H': 5812,   # Restaurants/Hotels
    'C': 5411,   # Consumer goods
    'S': 4899,   # Services
    'R': 5999    # Retail
}
df['merchant_mcc'] = df['ProductCD'].map(product_to_mcc).fillna(5999).astype(int)

# Card type: physical vs virtual (approximated from card info)
# card4: discover, mastercard, visa, american express
# card6: credit, debit, charge, debit or credit
df['card_type'] = (df['card6'] == 'credit').astype(int)  # 1=credit, 0=debit

# Channel from DeviceType
# DeviceType: desktop, mobile
df['channel'] = 2  # Default to POS
df.loc[df['DeviceType'] == 'desktop', 'channel'] = 1  # Web
df.loc[df['DeviceType'] == 'mobile', 'channel'] = 0   # App

# International flag from card country
# card3 = card country (numeric)
# If card3 != most common value, consider international
most_common_country = df['card3'].mode()[0] if not df['card3'].mode().empty else 150
df['is_international'] = (df['card3'] != most_common_country).astype(int)

# Night/Weekend flags
df['is_night'] = ((df['trans_hour'] >= 23) | (df['trans_hour'] <= 5)).astype(int)
df['is_weekend'] = (df['trans_day'] >= 5).astype(int)

# Distance category (use addr1/addr2 difference as proxy)
# addr1 = billing region, addr2 = billing postal
df['distance_category'] = 0  # Local by default
df.loc[df['addr1'].isna() | df['addr2'].isna(), 'distance_category'] = 2  # Unknown = medium risk

# City population proxy from addr1 (larger numbers = larger cities)
df['city_pop'] = df['addr1'].fillna(100).clip(upper=1000) * 1000

# Email domain risk (some domains are higher risk)
high_risk_domains = ['protonmail', 'yahoo', 'hotmail', 'outlook']
df['email_risk'] = 0
if 'P_emaildomain' in df.columns:
    for domain in high_risk_domains:
        df.loc[df['P_emaildomain'].str.contains(domain, na=False, case=False), 'email_risk'] = 1

print(f"✓ Features engineered")

# ============================================================================
# 3. Prepare training data
# ============================================================================
print("\n🎯 Preparing training data...")

# Features matching our existing model interface
feature_cols = [
    'amount',               # TransactionAmt (renamed)
    'trans_hour',
    'trans_day',
    'merchant_mcc',
    'card_type',
    'channel',
    'is_international',
    'is_night',
    'is_weekend',
    'amount_category',
    'distance_category',
    'city_pop'
]

# Also add some IEEE-CIS specific features that improve detection
extended_features = [
    'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10',
    'C11', 'C12', 'C13', 'C14',  # Count features
    'D1', 'D2', 'D3', 'D4', 'D5',  # Time delta features
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',  # Vesta features
]

# Only include extended features that exist
extended_available = [f for f in extended_features if f in df.columns]
all_features = feature_cols + extended_available

print(f"✓ Base features: {len(feature_cols)}")
print(f"✓ Extended features: {len(extended_available)}")
print(f"✓ Total features: {len(all_features)}")

X = df[all_features].copy()
y = df['isFraud'].copy()

# Handle missing values
X = X.fillna(0)

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

# Clean up memory
del df
gc.collect()

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
    'num_leaves': 64,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'scale_pos_weight': scale_pos_weight,
    'verbose': -1,
    'n_jobs': -1
}

train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=200,
    valid_sets=[test_data],
    callbacks=[lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=20)]
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
print("TOP 20 FEATURE IMPORTANCE")
print("=" * 60)

importance = model.feature_importance(importance_type='gain')
feature_importance = pd.DataFrame({
    'feature': all_features,
    'importance': importance
}).sort_values('importance', ascending=False)

print(feature_importance.head(20).to_string(index=False))

# ============================================================================
# 8. Save model (base features only for compatibility)
# ============================================================================
print("\n💾 Saving model...")

# Save the full model
model.save_model('artifacts/models/fraud_lgbm_ieee.bin')
print(f"✓ Model saved to artifacts/models/fraud_lgbm_ieee.bin")

# Train a simplified model with only base features for API compatibility
print("\n🔄 Training simplified model for API compatibility...")

X_base = X_train[feature_cols]
X_test_base = X_test[feature_cols]

train_data_base = lgb.Dataset(X_base, label=y_train)
test_data_base = lgb.Dataset(X_test_base, label=y_test, reference=train_data_base)

model_base = lgb.train(
    params,
    train_data_base,
    num_boost_round=200,
    valid_sets=[test_data_base],
    callbacks=[lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=0)]
)

auc_base = roc_auc_score(y_test, model_base.predict(X_test_base))
print(f"✓ Base model AUC: {auc_base:.6f}")

# Save base model as the main Kaggle model (for compatibility)
model_base.save_model('artifacts/models/fraud_lgbm_kaggle.bin')
print(f"✓ Base model saved to artifacts/models/fraud_lgbm_kaggle.bin (replaces old model)")

# ============================================================================
# 8b. Score Stretching Calibration
# ============================================================================
print("\n🌡️  Applying score stretching calibration...")

# Get raw predictions on validation set
raw_scores_test = model_base.predict(X_test_base)

# Analyze current score distribution
fraud_scores = raw_scores_test[y_test == 1]
legit_scores = raw_scores_test[y_test == 0]

print(f"\n📊 Raw score distribution:")
print(f"  Fraud: mean={fraud_scores.mean():.4f}, median={np.median(fraud_scores):.4f}")
print(f"  Legit: mean={legit_scores.mean():.4f}, median={np.median(legit_scores):.4f}")
print(f"  Separation: {fraud_scores.mean() - legit_scores.mean():.4f}")

# Strategy: Use percentile-based stretching optimized for low false positives
# Goal: minimize false positives (legit in DENY) while keeping good fraud detection
# Target: legit P90 -> 0.50 (so 90% of legit are ALLOW)
#         fraud P50 -> 0.75 (so 50% of fraud are DENY)

legit_median = np.median(legit_scores)
fraud_median = np.median(fraud_scores)
legit_p90 = np.percentile(legit_scores, 90)  # 90th percentile of legit
legit_p75 = np.percentile(legit_scores, 75)
fraud_p25 = np.percentile(fraud_scores, 25)

print(f"  Legit P75: {legit_p75:.4f}")
print(f"  Legit P90: {legit_p90:.4f}")
print(f"  Fraud P25: {fraud_p25:.4f}")

# Linear mapping: score' = a * score + b
# We want: legit_p90 -> 0.50 (so 90% of legit are ALLOW)
#          fraud_median -> 0.75 (so 50% of fraud are in DENY)
# 0.50 = a * legit_p90 + b
# 0.75 = a * fraud_median + b
# => a = 0.25 / (fraud_median - legit_p90)
# => b = 0.50 - a * legit_p90

stretch_a = 0.25 / (fraud_median - legit_p90)
stretch_b = 0.50 - stretch_a * legit_p90

print(f"\n✓ Stretching parameters:")
print(f"  Scale (a): {stretch_a:.4f}")
print(f"  Offset (b): {stretch_b:.4f}")
print(f"  Formula: calibrated = {stretch_a:.4f} * raw + {stretch_b:.4f}")

# Apply stretching and clip to [0, 1]
stretched_scores = np.clip(stretch_a * raw_scores_test + stretch_b, 0.0, 1.0)

# Analyze stretched distribution
stretched_fraud = stretched_scores[y_test == 1]
stretched_legit = stretched_scores[y_test == 0]

print(f"\n📊 Stretched score distribution:")
print(f"  Fraud: mean={stretched_fraud.mean():.4f}, median={np.median(stretched_fraud):.4f}")
print(f"  Legit: mean={stretched_legit.mean():.4f}, median={np.median(stretched_legit):.4f}")
print(f"  Separation: {stretched_fraud.mean() - stretched_legit.mean():.4f}")

# Verify AUC is preserved (linear transform preserves ranking)
auc_raw = roc_auc_score(y_test, raw_scores_test)
auc_stretched = roc_auc_score(y_test, stretched_scores)
print(f"\n✓ AUC preserved: {auc_raw:.6f} → {auc_stretched:.6f}")

# Save calibration parameters
calibration_params = {
    'method': 'linear_stretch',
    'scale': float(stretch_a),
    'offset': float(stretch_b),
    'legit_median_raw': float(legit_median),
    'fraud_median_raw': float(fraud_median)
}

with open('artifacts/models/score_calibrator.pkl', 'wb') as f:
    pickle.dump(calibration_params, f)
print(f"✓ Calibration params saved to artifacts/models/score_calibrator.pkl")

# Analyze threshold behavior with stretched scores
print(f"\n📊 Decision distribution with stretched scores (thresholds 0.50/0.70):")
for label, mask in [("Fraud", y_test == 1), ("Legit", y_test == 0)]:
    scores = stretched_scores[mask]
    allow = (scores < 0.50).mean() * 100
    challenge = ((scores >= 0.50) & (scores < 0.70)).mean() * 100
    deny = (scores >= 0.70).mean() * 100
    print(f"  {label}: ALLOW {allow:.1f}% | CHALLENGE {challenge:.1f}% | DENY {deny:.1f}%")

# ============================================================================
# 9. Save metadata
# ============================================================================
metadata = {
    'model_version': 'fraud_lgbm_ieee_v2_calibrated',
    'trained_at': datetime.now().isoformat(),
    'dataset': 'ieee-cis-fraud-detection',
    'n_samples': len(X_train) + len(X_test),
    'n_train': len(X_train),
    'n_test': len(X_test),
    'fraud_rate': float(y.mean()),
    'auc_score': float(auc_base),  # Base model AUC
    'auc_score_full': float(auc_score),  # Full model AUC
    'calibration': {
        'method': 'linear_stretch',
        'scale': float(stretch_a),
        'offset': float(stretch_b),
        'calibrator_file': 'score_calibrator.pkl'
    },
    'feature_names': feature_cols,
    'feature_importance': [
        {'feature': row['feature'], 'importance': float(row['importance'])}
        for _, row in feature_importance[feature_importance['feature'].isin(feature_cols)].iterrows()
    ]
}

with open('artifacts/models/fraud_model_metadata_ieee.json', 'w') as f:
    json.dump(metadata, f, indent=2)

# Also update the Kaggle metadata to point to new model
with open('artifacts/models/fraud_model_metadata_kaggle.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"✓ Metadata saved")

# ============================================================================
# 10. Verify amount category balance
# ============================================================================
print("\n" + "=" * 60)
print("FRAUD RATE BY AMOUNT CATEGORY (VERIFICATION)")
print("=" * 60)

X_test['isFraud'] = y_test.values
for cat in range(4):
    mask = X_test['amount_category'] == cat
    if mask.sum() > 0:
        fraud_rate = X_test.loc[mask, 'isFraud'].mean() * 100
        count = mask.sum()
        print(f"Category {cat}: {fraud_rate:.2f}% fraud ({count:,} transactions)")

print("\n" + "=" * 60)
print("✅ TRAINING COMPLETE!")
print("=" * 60)
print(f"Base Model AUC: {auc_base:.6f}")
print(f"Full Model AUC: {auc_score:.6f}")
print(f"Model: artifacts/models/fraud_lgbm_kaggle.bin (compatible with API)")
print(f"Features: {len(feature_cols)}")
