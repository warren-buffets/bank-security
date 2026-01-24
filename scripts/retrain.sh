#!/bin/bash
# FraudGuard AI - Model Retraining Script
# Usage: ./scripts/retrain.sh [--deploy]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

DEPLOY=${1:-""}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODEL_DIR="artifacts/models"
BACKUP_DIR="artifacts/models/backups"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         FRAUDGUARD AI - MODEL RETRAINING PIPELINE          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Backup current model
# ============================================================================
log_info "Step 1/5: Backing up current model..."

mkdir -p "$BACKUP_DIR"

if [ -f "$MODEL_DIR/fraud_lgbm_kaggle.bin" ]; then
    cp "$MODEL_DIR/fraud_lgbm_kaggle.bin" "$BACKUP_DIR/fraud_lgbm_kaggle_${TIMESTAMP}.bin"
    cp "$MODEL_DIR/fraud_model_metadata_kaggle.json" "$BACKUP_DIR/fraud_model_metadata_kaggle_${TIMESTAMP}.json" 2>/dev/null || true

    # Get old AUC for comparison
    OLD_AUC=$(python3 -c "import json; print(json.load(open('$MODEL_DIR/fraud_model_metadata_kaggle.json'))['auc_score'])" 2>/dev/null || echo "0")
    log_success "Backup created: backups/fraud_lgbm_kaggle_${TIMESTAMP}.bin"
    log_info "Previous AUC: $OLD_AUC"
else
    OLD_AUC="0"
    log_warn "No existing model to backup"
fi

# ============================================================================
# Step 2: Check training data
# ============================================================================
log_info "Step 2/5: Checking training data..."

if [ ! -f "artifacts/data/fraudTrain.csv" ]; then
    log_error "Training data not found: artifacts/data/fraudTrain.csv"
    exit 1
fi

DATA_SIZE=$(wc -l < "artifacts/data/fraudTrain.csv")
log_success "Training data found: $((DATA_SIZE - 1)) transactions"

# ============================================================================
# Step 3: Train new model
# ============================================================================
log_info "Step 3/5: Training new model..."
echo ""

python3 train_fraud_model_kaggle.py

echo ""

# ============================================================================
# Step 4: Compare models
# ============================================================================
log_info "Step 4/5: Comparing model performance..."

NEW_AUC=$(python3 -c "import json; print(json.load(open('$MODEL_DIR/fraud_model_metadata_kaggle.json'))['auc_score'])" 2>/dev/null || echo "0")

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                   MODEL COMPARISON                         ║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
printf "${CYAN}║${NC}  Previous AUC: %-43s${CYAN}║${NC}\n" "$OLD_AUC"
printf "${CYAN}║${NC}  New AUC:      %-43s${CYAN}║${NC}\n" "$NEW_AUC"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if new model is better
IMPROVED=$(python3 -c "print('yes' if float('$NEW_AUC') >= float('$OLD_AUC') else 'no')" 2>/dev/null || echo "yes")

if [ "$IMPROVED" = "yes" ]; then
    log_success "New model performance is equal or better!"
else
    log_warn "New model performance decreased. Consider rollback."
    log_info "Rollback command: cp $BACKUP_DIR/fraud_lgbm_kaggle_${TIMESTAMP}.bin $MODEL_DIR/fraud_lgbm_kaggle.bin"
fi

# ============================================================================
# Step 5: Deploy (optional)
# ============================================================================
if [ "$DEPLOY" = "--deploy" ]; then
    log_info "Step 5/5: Deploying new model..."

    # Check if model-serving is running
    if docker ps | grep -q "antifraud-model-serving"; then
        log_info "Restarting model-serving container..."
        docker restart antifraud-model-serving

        # Wait for health check
        sleep 5

        if curl -s http://localhost:8001/health | grep -q "healthy"; then
            log_success "Model deployed and service is healthy!"
        else
            log_warn "Service restarted but health check unclear"
        fi
    else
        log_warn "model-serving container not running. Start with: docker compose up -d"
    fi
else
    log_info "Step 5/5: Skipping deployment (use --deploy flag to auto-deploy)"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                   RETRAINING COMPLETE                      ║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Model:    $MODEL_DIR/fraud_lgbm_kaggle.bin"
echo -e "${CYAN}║${NC}  Backup:   $BACKUP_DIR/fraud_lgbm_kaggle_${TIMESTAMP}.bin"
echo -e "${CYAN}║${NC}  AUC:      $NEW_AUC"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Next steps:"
echo -e "${CYAN}║${NC}    • Test: ./scripts/ml-helper.sh batch_test"
echo -e "${CYAN}║${NC}    • Deploy: ./scripts/retrain.sh --deploy"
echo -e "${CYAN}║${NC}    • Rollback: cp backups/..._${TIMESTAMP}.bin fraud_lgbm_kaggle.bin"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
