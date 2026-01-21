#!/bin/bash
# Script de Vérification du Setup FraudGuard
# Usage: ./check-setup.sh

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Vérification du Setup FraudGuard ===${NC}"
echo ""

# Fonction pour afficher le statut
show_status() {
    local item="$1"
    local success="$2"
    local details="$3"

    if [ "$success" = "true" ]; then
        echo -ne "${GREEN}[OK]${NC} $item"
        if [ -n "$details" ]; then
            echo -e " - ${GRAY}$details${NC}"
        else
            echo ""
        fi
    else
        echo -ne "${RED}[X]${NC} $item"
        if [ -n "$details" ]; then
            echo -e " - ${YELLOW}$details${NC}"
        else
            echo ""
        fi
    fi
}

# 1. Vérifier Python
echo -e "${YELLOW}1. Python${NC}"
if command -v python &> /dev/null; then
    python_version=$(python --version 2>&1)
    show_status "Python installé" "true" "$python_version"
else
    show_status "Python installé" "false" "Non trouvé"
fi
echo ""

# 2. Vérifier les dépendances Python
echo -e "${YELLOW}2. Dépendances Python${NC}"
packages=("numpy" "pandas" "scikit-learn" "lightgbm" "fastapi" "uvicorn")
for pkg in "${packages[@]}"; do
    if pip show "$pkg" &> /dev/null; then
        version=$(pip show "$pkg" 2>/dev/null | grep "Version:" | cut -d' ' -f2)
        show_status "$pkg" "true" "$version"
    else
        show_status "$pkg" "false" "Non installé"
    fi
done
echo ""

# 3. Vérifier Docker
echo -e "${YELLOW}3. Docker${NC}"
if command -v docker &> /dev/null; then
    docker_version=$(docker --version 2>&1)
    show_status "Docker installé" "true" "$docker_version"

    # Vérifier si Docker daemon est lancé
    if docker info &> /dev/null; then
        show_status "Docker daemon actif" "true"
    else
        show_status "Docker daemon actif" "false" "Docker Desktop doit être lancé"
    fi
else
    show_status "Docker installé" "false" "Non trouvé - Voir INSTALL_DOCKER.md"
fi

if command -v docker &> /dev/null; then
    compose_version=$(docker compose version 2>&1)
    show_status "Docker Compose installé" "true" "$compose_version"
else
    show_status "Docker Compose installé" "false"
fi
echo ""

# 4. Vérifier les données Kaggle
echo -e "${YELLOW}4. Données Kaggle${NC}"
if [ -f "artifacts/data/fraudTrain.csv" ]; then
    show_status "fraudTrain.csv" "true" "335 MB"
else
    show_status "fraudTrain.csv" "false" "Manquant"
fi

if [ -f "artifacts/data/fraudTest.csv" ]; then
    show_status "fraudTest.csv" "true" "144 MB"
else
    show_status "fraudTest.csv" "false" "Manquant"
fi
echo ""

# 5. Vérifier les fichiers de configuration
echo -e "${YELLOW}5. Configuration${NC}"
if [ -f ".env" ]; then
    show_status ".env" "true"
else
    show_status ".env" "false"
fi

if [ -f "docker-compose.yml" ]; then
    show_status "docker-compose.yml" "true"
else
    show_status "docker-compose.yml" "false"
fi
echo ""

# 6. Vérifier les services (si Docker tourne)
echo -e "${YELLOW}6. Services Docker${NC}"
if docker info &> /dev/null; then
    containers=$(docker compose ps --format "{{.Service}}:{{.State}}" 2>/dev/null)
    if [ -n "$containers" ]; then
        while IFS=: read -r service state; do
            if [ "$state" = "running" ]; then
                show_status "$service" "true" "$state"
            else
                show_status "$service" "false" "$state"
            fi
        done <<< "$containers"
    else
        echo -e "${GRAY}Aucun conteneur en cours d'exécution${NC}"
        echo -e "${GRAY}Pour démarrer: docker compose up -d${NC}"
    fi
else
    echo -e "${YELLOW}Docker daemon non actif - impossible de vérifier les services${NC}"
fi
echo ""

# Résumé
echo -e "${CYAN}=== Résumé ===${NC}"
echo ""

all_ok=true

# Vérifier les prérequis critiques
if ! command -v python &> /dev/null; then
    echo -e "${RED}[!] Python n'est pas installé${NC}"
    all_ok=false
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}[!] Docker n'est pas installé - Voir INSTALL_DOCKER.md${NC}"
    all_ok=false
else
    if ! docker info &> /dev/null; then
        echo -e "${RED}[!] Docker Desktop n'est pas lancé${NC}"
        all_ok=false
    fi
fi

if [ ! -f "artifacts/data/fraudTrain.csv" ] || [ ! -f "artifacts/data/fraudTest.csv" ]; then
    echo -e "${RED}[!] Données Kaggle manquantes - Voir CLAUDE.md${NC}"
    all_ok=false
fi

if [ "$all_ok" = true ]; then
    echo -e "${GREEN}[OK] Setup complet - Prêt à démarrer!${NC}"
    echo ""
    echo -e "${CYAN}Pour démarrer les services:${NC}"
    echo -e "${NC}  docker compose up -d${NC}"
    echo ""
    echo -e "${CYAN}Pour vérifier la santé:${NC}"
    echo -e "${NC}  curl http://localhost:8000/health${NC}"
else
    echo ""
    echo -e "${YELLOW}Setup incomplet - Veuillez corriger les erreurs ci-dessus${NC}"
    echo -e "${GRAY}Consultez SETUP_STATUS.md pour plus de détails${NC}"
fi
