#!/bin/bash
# SafeGuard AI - Kubernetes Helper Script
# Usage: ./scripts/k8s-helper.sh [command]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

NAMESPACE="${K8S_NAMESPACE:-safeguard}"
CONTEXT="${K8S_CONTEXT:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Set context if provided
if [ -n "$CONTEXT" ]; then
    kubectl config use-context "$CONTEXT"
fi

# Apply raw manifests
apply_manifests() {
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f deploy/k8s-manifests/ -n "$NAMESPACE"
    log_success "Manifests applied."
}

# Deploy with Helm
helm_install() {
    local release_name=${1:-safeguard}
    local values_file=${2:-deploy/helm/safeguard/values.yaml}

    log_info "Installing/upgrading Helm release: $release_name"
    helm upgrade --install "$release_name" deploy/helm/safeguard \
        --namespace "$NAMESPACE" \
        --create-namespace \
        -f "$values_file" \
        --wait \
        --timeout 600s
    log_success "Helm release deployed."
}

# Uninstall Helm release
helm_uninstall() {
    local release_name=${1:-safeguard}
    log_info "Uninstalling Helm release: $release_name"
    helm uninstall "$release_name" --namespace "$NAMESPACE"
    log_success "Helm release removed."
}

# Get pod status
pods() {
    log_info "Pods in namespace $NAMESPACE:"
    kubectl get pods -n "$NAMESPACE" -o wide
}

# Get all resources
status() {
    log_info "SafeGuard status in namespace $NAMESPACE:"
    echo ""
    echo "=== Deployments ==="
    kubectl get deployments -n "$NAMESPACE"
    echo ""
    echo "=== Pods ==="
    kubectl get pods -n "$NAMESPACE"
    echo ""
    echo "=== Services ==="
    kubectl get services -n "$NAMESPACE"
    echo ""
    echo "=== HPA ==="
    kubectl get hpa -n "$NAMESPACE" 2>/dev/null || echo "No HPA found"
}

# View logs
logs() {
    local deployment=${1:-decision-engine}
    local follow=${2:-}

    log_info "Logs for $deployment:"
    if [ "$follow" = "-f" ]; then
        kubectl logs -f -l app.kubernetes.io/name="$deployment" -n "$NAMESPACE" --all-containers
    else
        kubectl logs -l app.kubernetes.io/name="$deployment" -n "$NAMESPACE" --all-containers --tail=100
    fi
}

# Shell into pod
shell() {
    local deployment=${1:-decision-engine}
    local pod=$(kubectl get pod -l app.kubernetes.io/name="$deployment" -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$pod" ]; then
        log_error "No pod found for $deployment"
        exit 1
    fi

    log_info "Opening shell in $pod..."
    kubectl exec -it "$pod" -n "$NAMESPACE" -- /bin/sh
}

# Port forward to a service
port_forward() {
    local service=${1:-decision-engine}
    local local_port=${2:-8000}
    local remote_port=${3:-8000}

    log_info "Port forwarding $service: localhost:$local_port -> $remote_port"
    kubectl port-forward svc/"$service" "$local_port:$remote_port" -n "$NAMESPACE"
}

# Restart a deployment
restart() {
    local deployment=${1:-decision-engine}
    log_info "Restarting deployment: $deployment"
    kubectl rollout restart deployment/"$deployment" -n "$NAMESPACE"
    kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=120s
    log_success "$deployment restarted."
}

# Scale a deployment
scale() {
    local deployment=${1:-decision-engine}
    local replicas=${2:-3}
    log_info "Scaling $deployment to $replicas replicas..."
    kubectl scale deployment/"$deployment" --replicas="$replicas" -n "$NAMESPACE"
    log_success "$deployment scaled to $replicas."
}

# Get events
events() {
    log_info "Recent events in $NAMESPACE:"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -30
}

# Describe pod issues
describe() {
    local resource=${1:-pod}
    local name=${2:-}

    if [ -z "$name" ]; then
        kubectl describe "$resource" -n "$NAMESPACE"
    else
        kubectl describe "$resource" "$name" -n "$NAMESPACE"
    fi
}

# Run smoke test
smoke_test() {
    log_info "Running smoke test..."

    # Port forward temporarily
    kubectl port-forward svc/decision-engine 8000:8000 -n "$NAMESPACE" &
    PF_PID=$!
    sleep 3

    # Test
    curl -s -X POST http://localhost:8000/v1/score \
        -H "Content-Type: application/json" \
        -d '{
            "event_id": "k8s_smoke_test",
            "idempotency_key": "k8s_'$(date +%s)'",
            "amount": 100.00,
            "currency": "EUR",
            "card_id": "card_k8s_test",
            "merchant_id": "merch_test",
            "merchant_mcc": "5411",
            "channel": "pos",
            "card_type": "physical"
        }' | jq .

    # Cleanup
    kill $PF_PID 2>/dev/null
    log_success "Smoke test complete."
}

# Get metrics
metrics() {
    log_info "Resource metrics:"
    kubectl top pods -n "$NAMESPACE" 2>/dev/null || log_warn "Metrics server not available"
}

# Show help
help() {
    echo "SafeGuard AI - Kubernetes Helper"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Deployment:"
    echo "  apply_manifests      Apply raw K8s manifests"
    echo "  helm_install [name]  Install/upgrade with Helm"
    echo "  helm_uninstall       Remove Helm release"
    echo ""
    echo "Status:"
    echo "  pods                 List pods"
    echo "  status               Show all resources"
    echo "  events               Show recent events"
    echo "  metrics              Show resource metrics"
    echo ""
    echo "Operations:"
    echo "  logs [deploy] [-f]   View logs (optional follow)"
    echo "  shell [deploy]       Shell into pod"
    echo "  port_forward [svc]   Forward port to service"
    echo "  restart [deploy]     Restart deployment"
    echo "  scale [deploy] [n]   Scale deployment"
    echo "  describe [type] [n]  Describe resource"
    echo "  smoke_test           Run API smoke test"
    echo ""
    echo "Environment:"
    echo "  K8S_NAMESPACE=$NAMESPACE"
    echo "  K8S_CONTEXT=$CONTEXT"
}

# Main
case "${1:-help}" in
    apply_manifests) apply_manifests ;;
    helm_install) helm_install "$2" "$3" ;;
    helm_uninstall) helm_uninstall "$2" ;;
    pods) pods ;;
    status) status ;;
    logs) logs "$2" "$3" ;;
    shell) shell "$2" ;;
    port_forward) port_forward "$2" "$3" "$4" ;;
    restart) restart "$2" ;;
    scale) scale "$2" "$3" ;;
    events) events ;;
    describe) describe "$2" "$3" ;;
    smoke_test) smoke_test ;;
    metrics) metrics ;;
    help|*) help ;;
esac
