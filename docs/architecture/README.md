# Architecture Diagrams - SafeGuard Financial

Ce dossier contient les diagrammes d'architecture C4 et de séquence pour SafeGuard Financial.

## 📐 Diagrammes Disponibles

### C4 Model

1. **[c4-level1-context.puml](c4-level1-context.puml)** - Diagramme de Contexte (Level 1)
   - Vue d'ensemble du système
   - Acteurs externes (PSP, Alice, Marc, Kumar)
   - Interactions principales

2. **[c4-level2-container.puml](c4-level2-container.puml)** - Diagramme de Conteneurs (Level 2)
   - 8 microservices (Decision Engine, Model Serving, Rules Service, etc.)
   - Bases de données (PostgreSQL, Redis)
   - Message broker (Kafka)
   - Monitoring (Prometheus, Grafana)

### Séquence

3. **[sequence-suspicious-transaction.puml](sequence-suspicious-transaction.puml)** - Transaction Suspecte
   - Flux complet d'une transaction à haut risque
   - Scoring parallèle (ML + Règles)
   - SCA dynamique
   - Audit logs HMAC
   - Case Management

---

## 🎨 Génération des Diagrammes

### Option 1: PlantUML en ligne (Rapide)

1. Copie le contenu d'un fichier `.puml`
2. Va sur http://www.plantuml.com/plantuml/uml/
3. Colle le code et génère le diagramme
4. Télécharge en PNG/SVG

### Option 2: PlantUML CLI (Recommandé)

**Installation**:

```bash
# macOS
brew install plantuml

# Ubuntu/Debian
sudo apt-get install plantuml

# Windows
choco install plantuml
```

**Génération**:

```bash
# Tous les diagrammes
plantuml docs/architecture/*.puml

# Un seul diagramme
plantuml docs/architecture/c4-level1-context.puml

# Sortie PNG
plantuml -tpng docs/architecture/*.puml

# Sortie SVG (vectoriel)
plantuml -tsvg docs/architecture/*.puml
```

### Option 3: VS Code Extension

1. Installer l'extension "PlantUML" (jebbs.plantuml)
2. Ouvrir un fichier `.puml`
3. Appuyer sur `Alt+D` pour prévisualiser
4. Clic droit → "Export Current Diagram"

### Option 4: Docker (Isolation)

```bash
# Génération via Docker
docker run --rm -v $(pwd):/data plantuml/plantuml:latest \
  /data/docs/architecture/*.puml
```

---

## 📊 Diagrammes Exportés

Les diagrammes PNG/SVG générés sont ignorés par Git (`.gitignore`).

Pour générer localement:

```bash
cd /path/to/bank-security
plantuml -tpng docs/architecture/*.puml

# Résultat:
# docs/architecture/c4-level1-context.png
# docs/architecture/c4-level2-container.png
# docs/architecture/sequence-suspicious-transaction.png
```

---

## 🔗 Références

### C4 Model
- Site officiel: https://c4model.com/
- PlantUML C4: https://github.com/plantuml-stdlib/C4-PlantUML

### PlantUML
- Documentation: https://plantuml.com/
- Syntaxe Séquence: https://plantuml.com/sequence-diagram
- Exemples: https://real-world-plantuml.com/

---

## 📝 Modification des Diagrammes

Pour modifier un diagramme:

1. Éditer le fichier `.puml` correspondant
2. Régénérer avec `plantuml <fichier>.puml`
3. Vérifier le rendu PNG/SVG
4. Commit uniquement le `.puml` (pas le PNG)

**Conseil**: Utilise VS Code avec l'extension PlantUML pour prévisualiser en temps réel.

---

## ✅ Checklist Livraison

- [x] C4 Level 1 (Contexte)
- [x] C4 Level 2 (Conteneurs)
- [x] Diagramme de séquence (Transaction suspecte)
- [ ] C4 Level 3 (Composants) - Optionnel
- [ ] Diagramme déploiement - Optionnel

**Status**: ✅ Architecture documentée conformément aux exigences du contrat.

---

**Dernière mise à jour**: 24 janvier 2026
