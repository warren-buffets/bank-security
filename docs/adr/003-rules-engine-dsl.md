# ADR-003: Moteur de Règles avec DSL Custom

## Statut
✅ **Accepté** - Janvier 2025

## Contexte

La détection de fraude nécessite de combiner :
- **ML** : Patterns complexes, apprentissage continu
- **Règles métier** : Logique business explicite, compréhensible par non-tech

### Cas d'usage des règles

1. **Règles hard** (non négociables)
   - Montant > 10,000€ → Toujours CHALLENGE
   - IP blacklistée → Toujours DENY

2. **Règles de velocity**
   - Plus de 5 transactions en 1h → Suspect
   - Total > 5000€ en 24h → CHALLENGE

3. **Règles géographiques**
   - Pays IP ≠ Pays carte → Risque
   - Distance > 500km depuis dernière transaction → Suspect

### Exigences

- **Performance** : Évaluation < 10ms
- **Expressivité** : Syntaxe simple pour business users
- **Maintenabilité** : Règles modifiables sans redéploiement
- **Traçabilité** : Savoir quelles règles ont été déclenchées

---

## Décision

Implémenter un **moteur de règles custom** avec DSL (Domain-Specific Language) simple.

### Syntaxe DSL

```python
# Exemples de règles
rules = [
    {
        "id": "high_amount",
        "name": "Montant élevé",
        "condition": "amount > 5000",
        "score": 0.8,
        "action": "CHALLENGE"
    },
    {
        "id": "velocity_abuse",
        "name": "Velocity suspecte",
        "condition": "velocity_24h('amount') > 10000",
        "score": 0.9,
        "action": "DENY"
    },
    {
        "id": "geo_mismatch",
        "name": "Pays IP différent",
        "condition": "ip_country != card_country",
        "score": 0.6,
        "action": "REVIEW"
    },
    {
        "id": "blacklist",
        "name": "IP blacklistée",
        "condition": "ip_hash IN blacklist",
        "score": 1.0,
        "action": "DENY"
    }
]
```

### Opérateurs Supportés

```
Comparaisons : > < >= <= == !=
Logiques     : AND OR NOT
Membership   : IN (pour listes)
Fonctions    : velocity_24h(field), velocity_1h(field)
```

---

## Implémentation

### Évaluateur DSL

```python
class RuleDSLEvaluator:
    """Évalue des expressions DSL simples."""

    def evaluate(self, condition: str, context: dict) -> bool:
        """
        Évalue une condition sur un contexte.

        Args:
            condition: "amount > 1000 AND geo != user_home_geo"
            context: {"amount": 1500, "geo": "BR", ...}

        Returns:
            True si condition vraie, False sinon
        """
        # 1. Parser la condition
        tokens = self._tokenize(condition)

        # 2. Évaluer récursivement
        return self._eval_expr(tokens, context)

    def _eval_expr(self, tokens, context):
        """Évaluation récursive avec gestion des opérateurs logiques."""
        # Gestion AND, OR, NOT
        # Gestion comparaisons
        # Gestion fonctions (velocity_24h, etc.)
        pass
```

### Engine Principal

```python
class RulesEngine:
    """Moteur de règles principal."""

    def __init__(self, rules: List[dict]):
        self.rules = rules
        self.evaluator = RuleDSLEvaluator()

    async def evaluate_all(self, context: dict) -> RulesResult:
        """Évalue toutes les règles."""
        triggered = []
        max_score = 0.0

        for rule in self.rules:
            try:
                if self.evaluator.evaluate(rule["condition"], context):
                    triggered.append(rule["id"])
                    max_score = max(max_score, rule["score"])

            except Exception as e:
                logger.error(f"Rule {rule['id']} failed: {e}")
                # Fail gracefully : skip rule

        return RulesResult(
            score=max_score,
            triggered_rules=triggered,
            action=self._determine_action(max_score)
        )
```

---

## Conséquences

### ✅ Positives

1. **Contrôle business**
   - Équipe métier peut ajouter/modifier règles facilement
   - Pas besoin de coder en Python

2. **Performance**
   - Évaluation en mémoire = ~1-5ms
   - Plus rapide que SQL queries

3. **Traçabilité**
   - Chaque décision retourne `triggered_rules: ["high_amount", "geo_mismatch"]`
   - Debuggable et explicable

4. **Flexibilité**
   - Règles stockées en JSON/YAML
   - Modifiables sans redéploiement (via API)

5. **Testabilité**
   - Règles faciles à tester unitairement

### ❌ Négatives

1. **DSL limité**
   - Pas de boucles, fonctions custom complexes
   - Pour logique avancée, besoin de coder en Python

2. **Parsing overhead**
   - Parsing de chaînes de caractères à chaque requête
   - Mitigation : Cache des règles parsées

3. **Sécurité**
   - Risque d'injection si DSL mal sécurisé
   - Mitigation : Whitelist des opérateurs, sandbox

4. **Maintenance custom code**
   - Besoin de maintenir notre propre parser
   - Bugs potentiels dans l'évaluateur

---

## Alternatives Évaluées

### Alternative 1 : Drools (Java Rule Engine)

**Description** : Moteur de règles mature et puissant

**Avantages** :
- ✅ Production-ready, mature
- ✅ Syntaxe DRL expressive
- ✅ Backward chaining, complex event processing

**Inconvénients** :
- ❌ Stack Java (notre stack = Python)
- ❌ Courbe d'apprentissage élevée
- ❌ Overhead JVM (~50-100ms startup)
- ❌ Over-engineered pour nos besoins simples

**Verdict** : ❌ Rejeté - Trop lourd, stack incompatible

### Alternative 2 : Python code direct (if/else)

**Description** : Écrire les règles directement en Python

```python
def evaluate_rules(context):
    if context["amount"] > 5000:
        return {"score": 0.8, "triggered": ["high_amount"]}
    # ...
```

**Avantages** :
- ✅ Performance maximale
- ✅ Puissance complète de Python

**Inconvénients** :
- ❌ Nécessite redéploiement pour chaque changement de règle
- ❌ Pas accessible aux non-développeurs
- ❌ Code spaghetti avec 50+ règles

**Verdict** : ❌ Rejeté - Pas assez flexible

### Alternative 3 : SQL queries

**Description** : Règles comme requêtes SQL

```sql
SELECT * FROM transactions
WHERE amount > 5000 OR velocity_24h > 10000;
```

**Avantages** :
- ✅ Syntaxe connue
- ✅ Optimiseur SQL

**Inconvénients** :
- ❌ Latence DB (5-10ms minimum)
- ❌ Velocity checks difficiles à implémenter
- ❌ Pas adapté à l'évaluation en temps réel

**Verdict** : ❌ Rejeté - Latence trop élevée

### Alternative 4 : Rego (Open Policy Agent)

**Description** : Langage déclaratif pour policy evaluation

**Avantages** :
- ✅ Production-ready (CNCF)
- ✅ Syntaxe déclarative claire

**Inconvénients** :
- ❌ Courbe d'apprentissage
- ❌ Dépendance externe (OPA server)
- ❌ Over-engineered pour fraud rules

**Verdict** : ❌ Rejeté - Trop complexe pour nos besoins

---

## Fonctions Spéciales

### Velocity Functions

```python
# Implémentation Redis
async def velocity_24h(field: str, user_id: str) -> float:
    """Somme d'un champ sur les 24 dernières heures."""
    key = f"velocity:24h:{user_id}:{field}"
    return float(await redis.get(key) or 0.0)

# Mise à jour après chaque transaction
await redis.zincrby(
    f"velocity:24h:{user_id}:amount",
    amount,
    timestamp
)
await redis.expire(key, 86400)  # TTL 24h
```

### Blacklist/Whitelist

```python
async def check_blacklist(ip_hash: str) -> bool:
    """Vérifie si IP est blacklistée."""
    return await redis.sismember("blacklist:ip", ip_hash)
```

---

## Stockage des Règles

### Format JSON

```json
{
  "rules": [
    {
      "id": "high_amount",
      "name": "Montant élevé",
      "enabled": true,
      "priority": 1,
      "condition": "amount > 5000",
      "score": 0.8,
      "action": "CHALLENGE",
      "metadata": {
        "owner": "fraud-team",
        "updated_at": "2025-01-20"
      }
    }
  ]
}
```

### Chargement Dynamique

```python
# Charger depuis fichier
rules = RulesEngine.load_from_file("rules/production.json")

# Charger depuis DB (pour hot-reload)
rules = RulesEngine.load_from_db(postgres_conn)

# Hot-reload via endpoint
@app.post("/admin/reload-rules")
async def reload_rules():
    global rules_engine
    rules_engine = RulesEngine.load_from_file("rules/production.json")
    return {"status": "reloaded"}
```

---

## Tests

```python
def test_high_amount_rule():
    """Test règle montant élevé."""
    rule = {"condition": "amount > 5000", "score": 0.8}

    # Test positif
    context = {"amount": 6000}
    assert evaluator.evaluate(rule["condition"], context) == True

    # Test négatif
    context = {"amount": 3000}
    assert evaluator.evaluate(rule["condition"], context) == False

def test_velocity_rule():
    """Test règle velocity."""
    rule = {"condition": "velocity_24h('amount') > 10000"}

    # Mock Redis
    with mock_redis({"velocity:24h:user1:amount": 12000}):
        context = {"user_id": "user1"}
        assert evaluator.evaluate(rule["condition"], context) == True
```

---

## Monitoring

### Métriques

```python
rules_evaluated_total = Counter("rules_evaluated_total", ["rule_id"])
rules_triggered_total = Counter("rules_triggered_total", ["rule_id"])
rules_errors_total = Counter("rules_errors_total", ["rule_id"])

# Taux de déclenchement par règle
trigger_rate_per_rule = rules_triggered_total / rules_evaluated_total
```

**Dashboard** : Visualiser les règles les plus déclenchées

---

## Évolution Future

1. **UI de gestion des règles** (Phase V2)
   - Interface web pour ajouter/modifier règles
   - Validation syntaxique en temps réel

2. **A/B Testing des règles** (Phase V2)
   - Tester impact business avant déploiement
   - Rollback automatique si métrique dégrade

3. **ML-assisted rules** (Phase V3)
   - Générer automatiquement des règles depuis patterns ML
   - "If amount > X AND country = BR then fraud probability > 80%"

---

## Références

- [Stripe: Rules Engine](https://stripe.com/docs/radar/rules)
- [Martin Fowler: Business Rules Engine](https://martinfowler.com/bliki/RulesEngine.html)
- [PayPal: Risk Rules System](https://medium.com/paypal-tech/the-next-generation-of-paypals-risk-engine-d0c94e9b)
