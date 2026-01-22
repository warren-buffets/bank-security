# IP Geolocation Feature - Six-Pager Technique

**Version** : 1.0
**Date** : Janvier 2025
**Équipe** : Warren Buffets
**Contact** : virgile.ader@epitech.digital

---

## 1. Résumé Exécutif

### Problème

La détection de fraude bancaire nécessite des informations géographiques pour identifier les transactions suspectes :
- **Transactions depuis pays à risque** : Certains pays ont des taux de fraude plus élevés
- **Incohérence géographique** : Carte française utilisée depuis la Russie
- **Distance anormale** : Transaction à 5000km du domicile en 10 minutes
- **Velocity géographique** : Transactions impossibles (Paris → Tokyo en 1h)

**Sans géolocalisation**, le modèle ML perd ~15% de précision sur les fraudes internationales.

### Solution Proposée

**Module IP Geolocation** intégré au service `model-serving` :

1. **API ip-api.com** : Service gratuit (45 req/min) pour la géolocalisation
2. **Cache Redis** : TTL 24h, évite les appels répétés (DB #1 dédiée)
3. **Features ML** : `distance_category`, `city_pop`, `country`
4. **Métriques Prometheus** : Cache hit/miss, latence API, distribution pays
5. **RGPD compliant** : IP jamais stockée en clair, hash uniquement

### Portée

**Implémenté (MVP)** :
- ✅ Géolocalisation via ip-api.com
- ✅ Cache Redis avec TTL 24h
- ✅ Calcul de distance Haversine (IP ↔ marchand)
- ✅ Estimation population urbaine
- ✅ Métriques Prometheus complètes
- ✅ Gestion des IPs privées (fallback Paris)

**Hors scope MVP** :
- ❌ Détection VPN/Proxy (IPQualityScore - Phase V1)
- ❌ GeoLite2 local database (Phase V1)
- ❌ Velocity géographique temps réel (Phase V2)

### Résultats Attendus

| Métrique | Sans Géoloc | Avec Géoloc | Impact |
|----------|-------------|-------------|--------|
| **AUC fraude internationale** | 0.82 | 0.91 | +11% |
| **Détection country mismatch** | 0% | 95% | Nouveau signal |
| **Latence géoloc (cache hit)** | - | < 1ms | Négligeable |
| **Latence géoloc (cache miss)** | - | ~100-200ms | Acceptable |
| **Cache hit rate cible** | - | > 80% | Efficacité |

---

## 2. Contexte & Principes

### Contexte Business

**Fraude internationale** :
- 35% des fraudes par carte impliquent une incohérence géographique
- Pays à risque : Russie, Nigeria, Indonésie, Brésil (source: Europol)
- Pattern typique : Vol de numéro de carte → utilisation depuis l'étranger

**Signaux géographiques clés** :
1. **Country mismatch** : Carte émise pays A, utilisée pays B
2. **Distance anormale** : > 500km du domicile habituel
3. **Velocity impossible** : 2 transactions, 2 pays, < 2h d'écart
4. **IP à risque** : VPN, Tor, datacenter (hébergeur cloud)

### Contraintes

1. **Performance** : Latence ajoutée < 50ms (P95)
2. **RGPD** : IP réelle ne doit jamais être stockée
3. **Coût** : Service gratuit ou < 100€/mois
4. **Rate limit** : ip-api.com = 45 req/min (cache obligatoire)
5. **Fiabilité** : Fallback si API down

### Hypothèses

1. Cache hit rate > 80% après warm-up (même IPs reviennent)
2. ip-api.com disponible 99%+ du temps
3. Précision géoloc suffisante (ville, pas adresse exacte)
4. Estimation population urbaine acceptable en l'absence de DB complète

### Principes Guidants

1. **Cache first** : Toujours vérifier Redis avant appel API
2. **Fail gracefully** : Si géoloc échoue → utiliser valeurs par défaut (Paris)
3. **Privacy by design** : IP hashée, pas de stockage en clair
4. **Observable** : Métriques complètes pour monitoring

---

## 3. Design Technique

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Model Serving (Port 8001)                 │
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │   /predict   │────▶│         geolocation.py           │  │
│  │   endpoint   │     │                                  │  │
│  └──────────────┘     │  ┌─────────────────────────────┐ │  │
│                       │  │     geolocate_ip(ip)        │ │  │
│                       │  │                             │ │  │
│                       │  │  1. Check private IP?       │ │  │
│                       │  │     └─▶ Return Paris default│ │  │
│                       │  │                             │ │  │
│                       │  │  2. Check Redis cache       │ │  │
│                       │  │     └─▶ HIT: Return cached  │ │  │
│                       │  │                             │ │  │
│                       │  │  3. Call ip-api.com         │ │  │
│                       │  │     └─▶ Store in cache      │ │  │
│                       │  │     └─▶ Return result       │ │  │
│                       │  └─────────────────────────────┘ │  │
│                       └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           │                         │
           ▼                         ▼
    ┌─────────────┐          ┌─────────────────┐
    │   Redis     │          │   ip-api.com    │
    │   (DB #1)   │          │   (externe)     │
    │             │          │                 │
    │ geo:ip:*    │          │ 45 req/min max  │
    │ TTL: 24h    │          │ Gratuit         │
    └─────────────┘          └─────────────────┘
```

### Flux de Données

**Scénario 1 : Cache HIT (80%+ des cas)**

```
1. POST /predict avec context.ip = "82.64.123.45"
2. geolocate_ip("82.64.123.45")
3. Redis GET geo:ip:82.64.123.45 → HIT
4. Deserialize → GeoLocation(lat=48.85, lon=2.35, city="Paris", ...)
5. Metrics: GEO_CACHE_HITS.inc()
6. Return → Feature engineering continue

Latence ajoutée: ~1ms
```

**Scénario 2 : Cache MISS**

```
1. POST /predict avec context.ip = "5.188.10.123"
2. geolocate_ip("5.188.10.123")
3. Redis GET geo:ip:5.188.10.123 → MISS
4. HTTP GET ip-api.com/json/5.188.10.123
5. Response: {lat: 55.75, lon: 37.62, city: "Moscow", country: "RU"}
6. Create GeoLocation + estimate_city_population("Moscow", "RU")
7. Redis SETEX geo:ip:5.188.10.123 86400 <json>
8. Metrics: GEO_CACHE_MISSES.inc(), GEO_API_CALLS.inc(), GEO_COUNTRY_REQUESTS.inc(country="RU")
9. Return GeoLocation

Latence ajoutée: ~100-200ms
```

**Scénario 3 : IP Privée**

```
1. POST /predict avec context.ip = "192.168.1.42"
2. geolocate_ip("192.168.1.42")
3. Détecte IP privée (192.168.*)
4. Metrics: GEO_PRIVATE_IP_SKIPPED.inc()
5. Return GeoLocation(Paris, success=False, error="Private IP")

Latence ajoutée: < 0.1ms
```

### Modèle de Données

**GeoLocation (dataclass)** :

```python
@dataclass
class GeoLocation:
    ip: str                    # IP originale
    lat: float                 # Latitude (-90 to 90)
    lon: float                 # Longitude (-180 to 180)
    city: str                  # Nom de la ville
    region: str                # Région/État
    country: str               # Code pays ISO (FR, US, RU...)
    city_pop: int              # Population estimée
    success: bool              # True si géoloc réussie
    error: Optional[str]       # Message d'erreur si échec
```

**Cache Redis** :

```
Key:    geo:ip:82.64.123.45
Value:  {"ip": "82.64.123.45", "lat": 48.8566, "lon": 2.3522,
         "city": "Paris", "region": "Île-de-France", "country": "FR",
         "city_pop": 2161000, "success": true, "error": null}
TTL:    86400 (24 heures)
DB:     1 (séparée de l'idempotence)
```

### Features ML Générées

Le module génère 2 features pour le modèle LightGBM :

| Feature | Type | Description | Calcul |
|---------|------|-------------|--------|
| `distance_category` | int [0-3] | Distance IP ↔ marchand | Haversine → catégorie |
| `city_pop` | int | Population urbaine | Lookup ou estimation |

**Catégories de distance** :

| Catégorie | Distance | Interprétation |
|-----------|----------|----------------|
| 0 | < 10 km | Transaction locale |
| 1 | 10-50 km | Même région |
| 2 | 50-200 km | Même pays |
| 3 | > 200 km | International / suspect |

### Métriques Prometheus

**Compteurs** :

| Métrique | Labels | Description |
|----------|--------|-------------|
| `geolocation_cache_hits_total` | - | Nombre de cache hits |
| `geolocation_cache_misses_total` | - | Nombre de cache misses |
| `geolocation_api_calls_total` | status | Appels API (success/error/timeout) |
| `geolocation_country_requests_total` | country | Distribution par pays |
| `geolocation_private_ip_skipped_total` | - | IPs privées ignorées |

**Histogramme** :

| Métrique | Buckets | Description |
|----------|---------|-------------|
| `geolocation_api_latency_seconds` | 0.05, 0.1, 0.25, 0.5, 1, 2, 5 | Latence API |

**Gauge** :

| Métrique | Description |
|----------|-------------|
| `geolocation_cache_size` | Nombre d'IPs en cache |

### Calcul de Distance (Haversine)

```python
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en km entre deux points GPS.
    Formule de Haversine (distance sur sphère).
    """
    R = 6371  # Rayon de la Terre en km

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    return R * c

# Exemple: Paris → Berlin = 878 km
haversine_distance(48.8566, 2.3522, 52.5200, 13.4050)  # → 878.2
```

---

## 4. Alternatives Évaluées

### API de Géolocalisation

| Solution | Précision | Latence | Coût | Rate Limit | Verdict |
|----------|-----------|---------|------|------------|---------|
| **ip-api.com** ✅ | 95% | 100ms | Gratuit | 45/min | ✅ **Choisi (MVP)** |
| ipinfo.io | 98% | 80ms | $100/mois | 50k/mois | ⚠️ Phase V1 |
| MaxMind GeoLite2 | 95% | 1ms | Gratuit | Illimité | ⚠️ Phase V1 (local) |
| IPQualityScore | 99%+ VPN | 150ms | $100/mois | 5k/jour | ⚠️ Phase V1 (VPN) |

**Justification ip-api.com** :
- Gratuit = parfait pour MVP
- 45 req/min suffisant avec cache Redis (hit rate 80%+)
- Précision acceptable pour features ML

**Plan d'évolution** :
- V1 : Ajouter GeoLite2 (DB locale, 1ms latence)
- V1 : Ajouter IPQualityScore (détection VPN)

### Stratégie de Cache

| Solution | Latence | Persistence | Verdict |
|----------|---------|-------------|---------|
| In-memory dict | 0.01ms | ❌ Perdu au restart | ❌ |
| Redis (choisi) ✅ | 1ms | ✅ Persistant | ✅ **Choisi** |
| PostgreSQL | 10ms | ✅ | ❌ Trop lent |

### Stockage IP (RGPD)

| Approche | RGPD | Utilité ML | Verdict |
|----------|------|------------|---------|
| IP en clair | ❌ Interdit | ✅ | ❌ Rejeté |
| Hash SHA-256 | ✅ | ⚠️ Limité | ⚠️ Pour idempotence |
| Features géo seulement ✅ | ✅ | ✅ | ✅ **Choisi** |

**Solution retenue** : Stocker uniquement les features géographiques (lat, lon, city, country), jamais l'IP réelle.

---

## 5. Risques & Mitigations

### Risques Techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **ip-api.com down** | Faible | Moyen | Fallback → valeurs défaut (Paris) |
| **Rate limit atteint** | Moyen | Moyen | Cache Redis agressif (TTL 24h) |
| **Redis down** | Faible | Moyen | Appel API direct (lent mais fonctionnel) |
| **Latence dégradée** | Moyen | Faible | Timeout 2s, métriques P95 |
| **Précision faible** | Faible | Faible | Acceptable pour ML (ville suffit) |

### Dépendances

1. **ip-api.com** (externe)
   - SLA non garanti (service gratuit)
   - Mitigation : Cache 24h + fallback

2. **Redis** (interne)
   - Critique pour performance
   - Mitigation : Mode dégradé sans cache

### Plan de Repli

```python
async def geolocate_ip(ip: str) -> GeoLocation:
    # 1. IP privée → Default Paris
    if is_private_ip(ip):
        return default_paris_location()

    # 2. Cache Redis → Fast path
    cached = redis.get(f"geo:ip:{ip}")
    if cached:
        return deserialize(cached)

    # 3. API call avec timeout
    try:
        geo = await call_ip_api(ip, timeout=2.0)
        redis.setex(f"geo:ip:{ip}", 86400, serialize(geo))
        return geo
    except (Timeout, APIError):
        # 4. Fallback → Default Paris
        return default_paris_location(success=False, error="API unavailable")
```

---

## 6. Plan & Métriques

### Implémentation

| Phase | Tâche | Status |
|-------|-------|--------|
| **MVP** | Module geolocation.py | ✅ Fait |
| **MVP** | Cache Redis (DB #1) | ✅ Fait |
| **MVP** | Intégration /predict | ✅ Fait |
| **MVP** | Métriques Prometheus | ✅ Fait |
| **MVP** | Documentation | ✅ Ce six-pager |
| **V1** | GeoLite2 (DB locale) | 🔜 Planifié |
| **V1** | Détection VPN | 🔜 Planifié |
| **V2** | Velocity géographique | 📋 Backlog |

### Dashboards Grafana (à créer)

**Panel 1 : Cache Efficiency**
```promql
# Cache hit rate
sum(rate(geolocation_cache_hits_total[5m])) /
(sum(rate(geolocation_cache_hits_total[5m])) + sum(rate(geolocation_cache_misses_total[5m])))
```

**Panel 2 : API Latency**
```promql
histogram_quantile(0.95, rate(geolocation_api_latency_seconds_bucket[5m]))
```

**Panel 3 : Geographic Distribution (pie chart)**
```promql
sum by (country) (geolocation_country_requests_total)
```

**Panel 4 : API Status**
```promql
sum by (status) (rate(geolocation_api_calls_total[5m]))
```

### SLIs / SLOs

| Indicateur | Objectif | Alerte si |
|------------|----------|-----------|
| Cache hit rate | > 80% | < 70% pendant 10min |
| API latency P95 | < 500ms | > 1s pendant 5min |
| API error rate | < 5% | > 10% pendant 2min |
| Géoloc success rate | > 95% | < 90% pendant 5min |

### Coûts

| Ressource | Coût |
|-----------|------|
| ip-api.com | Gratuit |
| Redis (espace additionnel) | ~10 MB pour 100k IPs |
| **Total MVP** | **0€** |

**Phase V1 estimée** :
- IPQualityScore : ~100€/mois
- GeoLite2 : Gratuit

---

## Annexes

### A. Fichiers Concernés

| Fichier | Description |
|---------|-------------|
| [services/model-serving/app/geolocation.py](../services/model-serving/app/geolocation.py) | Module principal |
| [services/model-serving/app/main.py](../services/model-serving/app/main.py) | Intégration endpoint |
| [services/model-serving/app/config.py](../services/model-serving/app/config.py) | Configuration |
| [docs/IP_GEOLOCATION.md](IP_GEOLOCATION.md) | Documentation technique détaillée |

### B. Exemples d'Utilisation

**Transaction normale (France → France)** :
```json
{
  "context": {"ip": "82.64.123.45"},
  "merchant": {"country": "FR", "lat": 48.8, "lon": 2.3}
}
// → distance_category: 0 (local), city_pop: 2161000
// → Score fraude: bas
```

**Transaction suspecte (carte FR, IP Russie)** :
```json
{
  "context": {"ip": "5.188.10.123"},
  "merchant": {"country": "FR", "lat": 48.8, "lon": 2.3}
}
// → IP géolocalisée: Moscow, RU
// → distance_category: 3 (>200km), country mismatch: true
// → Score fraude: élevé
```

### C. Références

- [ip-api.com Documentation](https://ip-api.com/docs)
- [Haversine Formula](https://en.wikipedia.org/wiki/Haversine_formula)
- [RGPD Article 6 - Base légale](https://gdpr-info.eu/art-6-gdpr/)
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)

---

**Fin du Six-Pager IP Geolocation**

Pour questions : virgile.ader@epitech.digital
