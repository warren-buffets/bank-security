# Pull Request: Database Migrations

## 📋 Description

Cette PR ajoute toutes les migrations de base de données PostgreSQL nécessaires pour FraudGuard AI.

## 🎯 Objectif

Créer le schéma complet de la base de données incluant toutes les tables, index, triggers et données de seed pour le système de détection de fraude.

## 📦 Contenu

### Fichiers ajoutés

- **V001__init.sql** - Création des tables principales
  - events, decisions, rules, lists, cases, labels, audit_logs
  
- **V002__indices.sql** - Index de performance
  - Index optimisés pour toutes les tables
  
- **V003__triggers.sql** - Triggers d immutabilité
  - Conformité audit trail et compliance
  
- **V004__seed_data.sql** - Données initiales
  - 7 règles de détection de fraude
  - Listes deny/allow

## ✅ Tests

- [x] Syntaxe SQL vérifiée (PostgreSQL 14+)
- [x] Tables créées avec succès
- [x] Indexes créés
- [x] Triggers fonctionnels

## 🚀 Déploiement

Appliquer les migrations dans l ordre: V001 -> V002 -> V003 -> V004

**Branch**: feature/database-migrations
**Files changed**: 4 files, 344 insertions(+)
