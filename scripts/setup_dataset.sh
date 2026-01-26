#!/bin/bash
# Script d'installation du dataset IEEE-CIS Fraud Detection
# Auteur: Virgile Ader
# Usage: ./scripts/setup_dataset.sh

set -e

# Définition des chemins
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/artifacts/data"
COMPETITION="ieee-fraud-detection"

# Couleurs
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}[INFO]${NC} Initialisation du dataset IEEE-CIS..."

# Vérification des pré-requis
if ! command -v kaggle &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} La commande 'kaggle' est introuvable."
    echo "👉 Veuillez l'installer : pip install kaggle"
    echo "👉 Et placez votre token dans ~/.kaggle/kaggle.json"
    exit 1
fi

# Création du répertoire
mkdir -p "$DATA_DIR"

# Téléchargement
echo -e "${BLUE}[INFO]${NC} Téléchargement des fichiers depuis Kaggle..."
kaggle competitions download -c "$COMPETITION" -p "$DATA_DIR"

# Extraction
echo -e "${BLUE}[INFO]${NC} Extraction et nettoyage..."
cd "$DATA_DIR"
unzip -o "${COMPETITION}.zip"
rm "${COMPETITION}.zip"

echo -e "${GREEN}[SUCCESS]${NC} Dataset installé avec succès dans :"
echo "$DATA_DIR"