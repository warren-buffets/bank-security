#!/bin/bash
# FraudGuard AI - ML Model Helper Script
# Usage: ./scripts/ml-helper.sh [command]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODEL_PATH="${MODEL_PATH:-artifacts/models}"
DATA_PATH="${DATA_PATH:-artifacts/data}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# List models
list_models() {
    log_info "Available models:"
    ls -lh "$MODEL_PATH"/*.bin 2>/dev/null || log_warn "No models found"
}

# Model info
model_info() {
    local model=${1:-fraud_lgbm_kaggle.bin}
    local model_file="$MODEL_PATH/$model"

    if [ ! -f "$model_file" ]; then
        log_warn "Model not found: $model_file"
        return 1
    fi

    log_info "Model: $model"
    echo "Path: $model_file"
    echo "Size: $(du -h "$model_file" | cut -f1)"
    echo "Modified: $(stat -f "%Sm" "$model_file" 2>/dev/null || stat -c "%y" "$model_file")"
}

# Test prediction
test_predict() {
    log_info "Testing model prediction..."

    curl -s -X POST http://localhost:8001/predict \
        -H "Content-Type: application/json" \
        -d '{
            "amount": 150.0,
            "trans_hour": 14,
            "trans_day": 2,
            "merchant_mcc": "5411",
            "card_type": "physical",
            "channel": "pos",
            "is_international": false,
            "merchant_city": "Paris"
        }' | python3 -m json.tool
}

# Batch test predictions
batch_test() {
    log_info "Running batch prediction test..."

    # Low risk
    log_info "Testing LOW RISK transaction..."
    curl -s -X POST http://localhost:8001/predict \
        -H "Content-Type: application/json" \
        -d '{"amount": 25.0, "trans_hour": 14, "trans_day": 2, "merchant_mcc": "5411", "card_type": "physical", "channel": "pos", "is_international": false}' \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Score: {d.get(\"score\", \"N/A\")}')"

    # Medium risk
    log_info "Testing MEDIUM RISK transaction..."
    curl -s -X POST http://localhost:8001/predict \
        -H "Content-Type: application/json" \
        -d '{"amount": 500.0, "trans_hour": 23, "trans_day": 6, "merchant_mcc": "5912", "card_type": "virtual", "channel": "web", "is_international": true}' \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Score: {d.get(\"score\", \"N/A\")}')"

    # High risk
    log_info "Testing HIGH RISK transaction..."
    curl -s -X POST http://localhost:8001/predict \
        -H "Content-Type: application/json" \
        -d '{"amount": 5000.0, "trans_hour": 3, "trans_day": 6, "merchant_mcc": "6051", "card_type": "virtual", "channel": "web", "is_international": true}' \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Score: {d.get(\"score\", \"N/A\")}')"

    log_success "Batch test complete."
}

# Check model serving health
health() {
    log_info "Checking model-serving health..."
    curl -s http://localhost:8001/health | python3 -m json.tool
}

# Get model metrics
metrics() {
    log_info "Model serving metrics:"
    curl -s http://localhost:8001/metrics | grep -E "^(model_|prediction_)" || echo "No model metrics found"
}

# Feature importance (requires Python)
feature_importance() {
    log_info "Feature importance analysis..."

    python3 << 'EOF'
import lightgbm as lgb
import os

model_path = os.environ.get('MODEL_PATH', 'artifacts/models')
model_file = os.path.join(model_path, 'fraud_lgbm_kaggle.bin')

try:
    model = lgb.Booster(model_file=model_file)
    importance = model.feature_importance(importance_type='gain')
    feature_names = model.feature_name()

    print("\nFeature Importance (by gain):")
    print("-" * 40)
    sorted_idx = sorted(range(len(importance)), key=lambda i: importance[i], reverse=True)
    for idx in sorted_idx:
        print(f"{feature_names[idx]:20} {importance[idx]:10.2f}")
except Exception as e:
    print(f"Error: {e}")
EOF
}

# Evaluate model (requires Python and test data)
evaluate() {
    log_info "Model evaluation (requires test data)..."

    python3 << 'EOF'
import lightgbm as lgb
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report
import os

model_path = os.environ.get('MODEL_PATH', 'artifacts/models')
data_path = os.environ.get('DATA_PATH', 'artifacts/data')

model_file = os.path.join(model_path, 'fraud_lgbm_kaggle.bin')
test_file = os.path.join(data_path, 'test.csv')

try:
    model = lgb.Booster(model_file=model_file)

    if os.path.exists(test_file):
        df = pd.read_csv(test_file)
        # Assuming 'is_fraud' is the label column
        if 'is_fraud' in df.columns:
            X = df.drop('is_fraud', axis=1)
            y = df['is_fraud']
            y_pred = model.predict(X)

            auc = roc_auc_score(y, y_pred)
            print(f"\nModel Evaluation Results:")
            print(f"-" * 40)
            print(f"AUC-ROC: {auc:.4f}")

            # Binary predictions at 0.5 threshold
            y_pred_binary = (y_pred > 0.5).astype(int)
            print(f"\nClassification Report (threshold=0.5):")
            print(classification_report(y, y_pred_binary, target_names=['Legitimate', 'Fraud']))
        else:
            print("No 'is_fraud' label column found")
    else:
        print(f"Test data not found: {test_file}")
        print("Generate predictions for manual evaluation")
except Exception as e:
    print(f"Error: {e}")
EOF
}

# Show help
help() {
    echo "FraudGuard AI - ML Model Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Model Info:"
    echo "  list_models          List available models"
    echo "  model_info [name]    Show model details"
    echo "  feature_importance   Show feature importance"
    echo ""
    echo "Testing:"
    echo "  test_predict         Test single prediction"
    echo "  batch_test           Test low/medium/high risk"
    echo "  evaluate             Evaluate on test data"
    echo ""
    echo "Monitoring:"
    echo "  health               Check model-serving health"
    echo "  metrics              Show Prometheus metrics"
    echo ""
    echo "Environment:"
    echo "  MODEL_PATH=$MODEL_PATH"
    echo "  DATA_PATH=$DATA_PATH"
}

# Main
case "${1:-help}" in
    list_models) list_models ;;
    model_info) model_info "$2" ;;
    feature_importance) feature_importance ;;
    test_predict) test_predict ;;
    batch_test) batch_test ;;
    evaluate) evaluate ;;
    health) health ;;
    metrics) metrics ;;
    help|*) help ;;
esac
