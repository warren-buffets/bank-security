# 📥 Setup du Dataset Kaggle - Fraud Detection

## Dataset à utiliser

**Nom**: Credit Card Fraud Detection
**URL**: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
**Taille**: ~150MB (284,807 transactions)
**Format**: CSV

## Installation Kaggle CLI

```bash
# Installer Kaggle CLI
pip install kaggle

# Configurer les credentials
# 1. Aller sur https://www.kaggle.com/settings
# 2. Créer un nouveau API token
# 3. Télécharger kaggle.json
# 4. Le placer dans ~/.kaggle/

mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

## Téléchargement du dataset

```bash
# Créer le dossier data
mkdir -p artifacts/data

# Télécharger le dataset
kaggle datasets download -d mlg-ulb/creditcardfraud -p artifacts/data

# Décompresser
cd artifacts/data
unzip creditcardfraud.zip
rm creditcardfraud.zip
cd ../..
```

## Structure du dataset

Le fichier `creditcard.csv` contient:

**Colonnes**:
- `Time`: Secondes écoulées depuis la première transaction
- `V1-V28`: Features anonymisées (PCA)
- `Amount`: Montant de la transaction
- `Class`: 0 = légitime, 1 = fraude

**Statistiques**:
- Total transactions: 284,807
- Fraudes: 492 (0.172%)
- Légitimes: 284,315 (99.828%)
- Déséquilibre de classe important!

## Alternative: Dataset synthétique amélioré

Si tu ne peux pas télécharger Kaggle, on peut générer un dataset synthétique plus réaliste.

