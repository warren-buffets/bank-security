# Architecture Decision Records (ADR)

## Qu'est-ce qu'un ADR ?

Un **Architecture Decision Record** (ADR) documente une décision architecturale importante, avec son contexte, les alternatives évaluées, et la justification du choix final.

## Format ADR

Chaque ADR suit cette structure :

```
# ADR-XXX: Titre de la Décision

## Statut
[Proposé | Accepté | Rejeté | Obsolète]

## Contexte
Quel est le problème à résoudre ?

## Décision
Quelle solution avons-nous choisie ?

## Conséquences
- Positives
- Négatives
- Risques

## Alternatives Évaluées
Quelles autres options avons-nous considérées et pourquoi les avons-nous rejetées ?
```

---

## Liste des ADR

### Infrastructure & Architecture

- [ADR-001: Architecture Microservices](001-microservices-architecture.md) - ✅ Accepté
- [ADR-002: Redis pour l'Idempotence](002-redis-idempotency.md) - ✅ Accepté
- [ADR-003: Moteur de Règles avec DSL](003-rules-engine-dsl.md) - ✅ Accepté
- [ADR-004: Kafka pour Event Streaming](004-kafka-event-streaming.md) - ✅ Accepté
- [ADR-007: PostgreSQL comme Base de Données](007-postgresql-storage.md) - ✅ Accepté

### Machine Learning

- [ADR-005: Stratégie de Géolocalisation IP](005-ip-geolocation-strategy.md) - ✅ Accepté
- [ADR-006: Calibration du Modèle (Platt Scaling)](006-model-calibration.md) - ✅ Accepté

---

## Principes Directeurs

Nos décisions architecturales sont guidées par ces principes :

1. **Performance d'abord** : P95 < 100ms, P99 < 200ms
2. **Résilience** : Fail gracefully, pas de single point of failure
3. **Observabilité** : Chaque service expose des métriques Prometheus
4. **RGPD compliance** : Anonymisation des données sensibles
5. **Scalabilité** : Horizontal scaling via Kubernetes
6. **Simplicité** : KISS - Keep It Simple, Stupid

---

## Comment Proposer un ADR ?

1. Copier le template [000-template.md](000-template.md)
2. Remplir les sections avec votre proposition
3. Numéroter avec le prochain ADR-XXX disponible
4. Soumettre en Pull Request avec le tag `adr`
5. Review par l'équipe technique
6. Si accepté : statut → "Accepté"

---

## Révisions d'ADR

Les ADR sont **immutables** une fois acceptés. Si une décision change :
- Créer un nouvel ADR qui **supersède** l'ancien
- Marquer l'ancien comme "Obsolète"
- Référencer le nouvel ADR

Exemple :
```
# ADR-002: Redis pour l'Idempotence

## Statut
Obsolète - Remplacé par [ADR-015](015-dynamodb-idempotency.md)
```

---

## Références

- [Architecture Decision Records (ThoughtWorks)](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)
- [ADR GitHub Template](https://github.com/joelparkerhenderson/architecture-decision-record)
