# ADR-002: Redis pour l'Idempotence

## Statut
✅ **Accepté** - Janvier 2025

## Contexte

Les systèmes de paiement doivent gérer les **requêtes en double** (duplicates) causées par :
- **Retry automatique** du client (timeout réseau)
- **Double-clic** utilisateur
- **Replay** malveillant

### Problème
Sans idempotence, une transaction peut être scorée 2+ fois, causant :
- Incohérence des métriques (double-counting)
- Consommation inutile de ressources
- Faux positifs (velocity mal calculée)

### Exigence
**Idempotency key** : Le client fournit une clé unique (`idempotency_key`) par transaction. Si la même clé arrive 2 fois, retourner le résultat de la 1ère requête sans recalcul.

---

## Décision

Utiliser **Redis** comme cache d'idempotence avec :
- **Clé** : `idem:{tenant_id}:{idempotency_key}`
- **Valeur** : `decision_id` (UUID de la décision)
- **TTL** : 24 heures (configurable)

### Implémentation

```python
class IdempotencyChecker:
    async def check_and_set(self, idempotency_key: str, decision_id: str) -> Optional[str]:
        """
        Vérifie si la requête est un duplicate.
        Returns:
            None si nouvelle requête
            decision_id existant si duplicate
        """
        redis_key = f"idem:{idempotency_key}"

        # 1. Vérifier si existe
        existing = await self.redis_client.get(redis_key)
        if existing:
            logger.info(f"Duplicate detected: {idempotency_key}")
            return existing  # Retourner l'ID de la décision existante

        # 2. Sinon, stocker pour 24h
        await self.redis_client.setex(
            redis_key,
            86400,  # 24h TTL
            decision_id
        )
        return None  # Nouvelle requête
```

### Workflow

```
Client request avec idempotency_key = "tx-20250120-abc123"
    │
    ▼
┌─────────────────┐
│ Decision Engine │
└────────┬────────┘
         │
         │ 1. Check Redis: idem:bank-fr:tx-20250120-abc123
         ▼
    ┌────────┐
    │ Redis  │
    └────┬───┘
         │
         ├─ Si EXISTS → Retourner decision_id existant (200 OK)
         │
         └─ Si NOT EXISTS → Continuer processing
                  │
                  │ 2. Scorer transaction
                  │ 3. Stocker dans Redis (TTL 24h)
                  │ 4. Retourner nouvelle décision
```

---

## Conséquences

### ✅ Positives

1. **Idempotence garantie**
   - Même requête = même résultat (≤ 24h)
   - Évite double-scoring et incohérences

2. **Performance**
   - Redis GET = ~1ms
   - SET avec TTL = ~1ms
   - Overhead négligeable

3. **Simplicité**
   - Code simple (check + set)
   - Pas besoin de DB transactionnelle

4. **TTL automatique**
   - Pas de nettoyage manuel
   - Mémoire libérée après 24h

5. **Scalabilité**
   - Redis supporte 100k+ ops/sec
   - Sharding possible si besoin

### ❌ Négatives

1. **Dépendance Redis**
   - Si Redis down → pas d'idempotence (fail open)
   - Mitigation : Redis Cluster (HA)

2. **Perte de mémoire**
   - Si Redis crash → clés perdues
   - Risque de re-processing pendant quelques secondes
   - Acceptable car non-critique

3. **TTL limité**
   - Après 24h, clé expirée → peut rescorer
   - Acceptable car peu probable (retries < 1h généralement)

---

## Alternatives Évaluées

### Alternative 1 : PostgreSQL

**Description** : Stocker idempotency keys dans une table SQL

```sql
CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    decision_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Avantages** :
- Persistance durable
- ACID guarantees

**Inconvénients** :
- ❌ Latence élevée (5-10ms vs 1ms Redis)
- ❌ Overhead DB (indexation, locking)
- ❌ Scalabilité limitée (write bottleneck)

**Verdict** : ❌ Rejeté - Latence trop élevée pour notre SLA

### Alternative 2 : In-Memory (dict local)

**Description** : Stocker dans un dict Python en mémoire

```python
idempotency_cache = {}  # Local dict
```

**Avantages** :
- Ultra rapide (~0.01ms)
- Pas de dépendance externe

**Inconvénients** :
- ❌ Pas partagé entre replicas
- ❌ Perdu au redémarrage
- ❌ Memory leak (pas de TTL automatique)

**Verdict** : ❌ Rejeté - Ne fonctionne pas en multi-replicas

### Alternative 3 : DynamoDB / Memcached

**Description** : Autres solutions de cache distribué

**DynamoDB** :
- ✅ Persistant, scalable
- ❌ Latence ~10ms (vs 1ms Redis)
- ❌ Coût élevé

**Memcached** :
- ✅ Performance similaire à Redis
- ❌ Pas de persistance
- ❌ Pas de TTL automatique par clé

**Verdict** : ❌ Rejetés - Redis offre le meilleur compromis

---

## Gestion des Cas Limites

### 1. Redis Down (Fail Open)

```python
try:
    existing = await redis_client.get(key)
except redis.ConnectionError:
    logger.warning("Redis unavailable, skipping idempotency check")
    return None  # Continuer sans idempotence
```

**Rationale** : Mieux scorer 2x que bloquer le système.

### 2. Race Condition (2 requêtes simultanées)

**Problème** : 2 requêtes identiques arrivent exactement en même temps

```
Request A → Check Redis (NOT EXISTS) → Process → Set Redis
Request B → Check Redis (NOT EXISTS) → Process → Set Redis
                ↑ Race condition
```

**Solution** : Utiliser `SETNX` (Set if Not Exists)

```python
success = await redis_client.setnx(key, decision_id)
if not success:
    # Quelqu'un d'autre a déjà set la clé
    existing = await redis_client.get(key)
    return existing
```

**Limitation** : Fenêtre de 1-2ms où les deux requêtes peuvent passer. **Acceptable** car très rare et non-critique.

### 3. TTL expiré pendant le processing

**Problème** : Clé expire entre le check et le set

**Solution** : Définir TTL long (24h) pour couvrir 99.99% des cas.

---

## Configuration

```python
# .env
REDIS_IDEMPOTENCY_TTL=86400  # 24 heures en secondes

# Pour tests : TTL court
REDIS_IDEMPOTENCY_TTL=60  # 1 minute
```

---

## Monitoring

### Métriques Prometheus

```python
idempotency_checks_total = Counter("idempotency_checks_total")
idempotency_hits_total = Counter("idempotency_hits_total")  # Duplicates détectés
idempotency_errors_total = Counter("idempotency_errors_total")  # Redis errors

# Taux de duplicates
duplicate_rate = idempotency_hits_total / idempotency_checks_total
```

**Alertes** :
- `duplicate_rate > 5%` → Possible retry storm
- `idempotency_errors_total > 10/min` → Redis issues

---

## Tests

```python
async def test_idempotency_duplicate_request():
    """Vérifier que duplicate retourne même décision."""
    key = "test-tx-123"

    # 1ère requête
    decision_id_1 = await score_transaction(key, event)
    assert decision_id_1 == "dec-uuid-1"

    # 2ème requête (duplicate)
    decision_id_2 = await score_transaction(key, event)
    assert decision_id_2 == "dec-uuid-1"  # Même décision

async def test_idempotency_redis_down():
    """Vérifier fail-open si Redis down."""
    # Simuler Redis down
    redis_client.close()

    decision_id = await score_transaction(key, event)
    assert decision_id is not None  # Processing continue
```

---

## Références

- [Stripe: Idempotent Requests](https://stripe.com/docs/api/idempotent_requests)
- [AWS: Implementing Idempotency](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [Redis: SETNX Command](https://redis.io/commands/setnx/)
