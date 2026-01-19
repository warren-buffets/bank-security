# Architecture Technique du Système d'Information – Projet de Détection de Fraude Bancaire

Ce document présente l'architecture logicielle et les choix technologiques pour la construction de la plateforme de détection de fraude en temps réel. Il a pour but de justifier les décisions techniques structurantes.

## 1. Vision Générale et Objectifs

L'objectif est de développer un système capable d'analyser les transactions bancaires en temps réel pour évaluer leur risque de fraude et permettre une prise de décision (blocage ou autorisation) en quelques centaines de millisecondes. Le système doit être hautement disponible, performant et capable d'évoluer pour intégrer de nouvelles logiques de détection.

## 2. Paradigmes et Choix d'Architecture

Les fondations du système reposent sur des décisions clés visant la maintenabilité et la scalabilité.

#### a. Architecture Microservices

*   **Principe :** Le système est décomposé en services indépendants, chacun avec une responsabilité unique et communiquant via des APIs bien définies.
*   **Alternative non retenue :** L'architecture **monolithique**. Bien que plus simple à démarrer, elle devient rapidement complexe à maintenir et à faire évoluer. Le moindre changement requiert de redéployer l'ensemble.
*   **Justification du choix :** L'approche microservices permet une **évolutivité ciblée**, une **résilience accrue** et une **maintenance simplifiée**.

#### b. Communication Asynchrone vs. Synchrone

*   **Principe :** Nous privilégions une communication asynchrone via un bus de messages pour les actions qui n'requirent pas une réponse immédiate (ex: notifier d'autres systèmes après une décision).
*   **Alternative non retenue :** La communication **synchrone par appels API REST directs** entre tous les services. Cela crée un couplage fort et des latences en chaîne si un service est lent.
*   **Justification du choix :** Le mode asynchrone garantit le **découplage** et la **résilience**. Il assure une meilleure gestion des pics de charge et une robustesse globale.

#### c. Conteneurisation (Docker)

*   **Principe :** Chaque microservice est packagé dans une image **Docker**, créant un artefact portable et isolé : le conteneur.
*   **Rôle dans le cycle de vie :** Il garantit la **cohérence des environnements** entre le développement, les tests et la production, éliminant les erreurs liées aux différences de configuration.
*   **Justification du choix :** Docker est le standard de l'industrie pour la **portabilité** et la **reproductibilité** des déploiements.

## 3. Flux de Données et Composants

#### a. Format de la Donnée en Entrée

Le système est déclenché par la réception d'un événement de transaction. Voici sa structure type en JSON :

```json
{
  "transaction_id": "c3f7c9e4-3c6c-4b8a-8b0e-2a4b6b1a3e7d",
  "user_id": "usr_12345",
  "amount": 97.50,
  "currency": "EUR",
  "timestamp_utc": "2025-12-18T14:35:12Z",
  "merchant_details": {
    "merchant_id": "merch_5678",
    "category": "online_retail"
  },
  "context": {
    "ip_address": "81.92.34.56",
    "device_id": "dev_abcde"
  }
}
```

#### b. Description des Composants Clés

*   **API Gateway (Portail d'Entrée)**
    *   **Rôle :** Point d'entrée unique pour les requêtes externes. Il est responsable de l'authentification, de la validation initiale et du routage vers le `decision-engine`.
    *   **Détails techniques :** Il découple les clients de l'architecture interne et peut agréger des résultats ou transformer les formats de requêtes.

*   **Decision Engine (Moteur de Décision)**
    *   **Rôle :** Le coordinateur du flux d'analyse. Il orchestre les appels aux services spécialisés.
    *   **Détails techniques :** Il effectue des appels parallèles (synchrones, car il a besoin d'une réponse rapide) au `rules-service` et au `model-serving`. Il collecte leurs réponses, applique une logique de décision finale et publie le résultat complet de l'analyse dans Kafka.

*   **Rules Service (Service de Règles)**
    *   **Rôle :** Évalue la transaction par rapport à un ensemble de règles déterministes (ex: listes de pays à risque, seuils de montant).
    *   **Détails techniques :** Les règles sont chargées en mémoire pour une évaluation rapide. Le service retourne des "flags" indiquant les règles qui ont été déclenchées.

*   **Model Serving (Service du Modèle d'IA)**
    *   **Rôle :** Calcule une probabilité de fraude en utilisant un modèle de Machine Learning.
    *   **Détails techniques :**
        1.  **Modèle sous-jacent :** Le service embarque un modèle de **classification** (ex: **LightGBM**, **XGBoost**). Ce modèle est entraîné hors ligne sur un jeu de données historique étiqueté (inspiré de datasets Kaggle) pour apprendre les schémas de fraude.
        2.  **Inférence en temps réel :** Le service expose une API (`POST /predict`). Il transforme les données brutes de la transaction en caractéristiques numériques (feature engineering) puis les passe au modèle pour obtenir un score de probabilité de fraude (entre 0 et 1).

*   **Bus de Messages (Apache Kafka)**
    *   **Rôle :** Composant central pour la communication asynchrone. Il sert de "mémoire tampon" fiable pour les événements.
    *   **Détails techniques :** Une fois l'analyse terminée, le `decision-engine` publie un message contenant tous les détails de la transaction et de la décision dans un "topic" Kafka. Des services en aval (non décrits ici, ex: un service d'archivage, de notification, ou d'alimentation d'un data warehouse) peuvent consommer ces messages sans jamais ralentir le processus de décision initial.
    *   **Alternative non retenue :** **RabbitMQ**. Bien que très capable, Kafka est spécialisé dans le traitement de flux d'événements à très haut débit et offre des garanties de persistance et de relecture des messages supérieures, ce qui est crucial pour un système d'audit comme le nôtre.

*   **Base de Données (PostgreSQL)**
    *   **Rôle :** Source de vérité pour les données "à chaud" et de configuration : informations utilisateurs, listes pour les règles, état des dossiers, etc.
    *   **Détails techniques :** En tant que base de données relationnelle, PostgreSQL garantit la cohérence forte des données via ses transactions ACID (Atomicité, Cohérence, Isolation, Durabilité).
    *   **Alternative non retenue :** Une base de données **NoSQL** (ex: MongoDB). Elle serait moins adaptée pour gérer les relations complexes et les garanties transactionnelles fortes dont nous avons besoin pour nos données de configuration.
