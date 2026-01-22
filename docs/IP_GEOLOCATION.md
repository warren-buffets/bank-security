# Géolocalisation IP - Choix Technique

## Contexte

Pour détecter les fraudes, nous devons enrichir les transactions avec des informations géographiques dérivées de l'adresse IP de l'utilisateur. Cependant, cela soulève des questions de :
- **Performance** (latence)
- **RGPD** (anonymisation)
- **Précision** (qualité des features ML)

## Problématique

**Question** : Comment extraire des features géographiques pertinentes à partir d'une IP sans :
1. Stocker l'IP réelle (violation RGPD)
2. Ajouter une latence excessive (objectif P95 < 100ms)
3. Perdre en précision ML

---

## Options Évaluées

### Option 1 : Hasher l'IP (Anonymisation complète)

**Description** :
```python
import hashlib

def hash_ip(ip_address: str) -> str:
    """Hash l'IP avec SHA-256."""
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

# Exemple
hash_ip("192.168.1.1")  # → "c775e7b757ede630"
```

**Avantages** :
- ✅ **RGPD-friendly** : IP réelle jamais stockée
- ✅ **Consistance** : Même IP → Même hash (utile pour velocity checks)
- ✅ **Rapide** : ~0.1ms de latence
- ✅ **Simple** : Pas de dépendance externe

**Inconvénients** :
- ❌ **Perte d'information géographique** : Impossible de savoir si IP est en France ou au Brésil
- ❌ **Pas de détection VPN/Proxy**
- ❌ **Features ML limitées** : Juste un hash opaque
- ❌ **Moins précis** : Le ML ne peut pas apprendre que "IP brésilienne + carte française = suspect"

**Use Case** :
- Détection de replay attacks (même IP répétée)
- Velocity checks simples (combien de fois cette IP en 1h ?)

---

### Option 2 : WHOIS / GeoIP Database (Enrichissement géographique)

**Description** :
```python
import geoip2.database

def get_geo_features(ip_address: str) -> dict:
    """Extrait features géo via MaxMind GeoLite2."""
    reader = geoip2.database.Reader('GeoLite2-City.mmdb')
    response = reader.city(ip_address)

    return {
        "country": response.country.iso_code,      # "FR"
        "region": response.subdivisions[0].iso_code,  # "IDF"
        "city": response.city.name,                # "Paris"
        "latitude": response.location.latitude,
        "longitude": response.location.longitude,
        "asn": get_asn(ip_address),               # Autonomous System Number
        "is_vpn": check_vpn(ip_address),          # Via IPQualityScore ou similar
    }
```

**Avantages** :
- ✅ **Features ML riches** : Pays, région, ville, ASN, VPN detection
- ✅ **Précision élevée** : Le ML peut apprendre "IP pays X + carte pays Y = risque"
- ✅ **Détection VPN/Proxy** : Identification des IPs suspectes
- ✅ **Distance géographique** : Calcul de distance entre IP et adresse facturation

**Inconvénients** :
- ❌ **Latence** : +5-20ms si appel API externe (MaxMind, IPInfo, IPQualityScore)
- ❌ **Coût** : Services payants (IPQualityScore ~0.001$/requête)
- ❌ **RGPD** : Nécessite de ne **pas stocker** l'IP, juste les features extraites
- ❌ **Précision variable** : GeoIP = ~95% précision pays, ~75% précision ville

**Solutions disponibles** :

| Service | Coût | Latence | Précision | VPN Detection |
|---------|------|---------|-----------|---------------|
| **MaxMind GeoLite2** (DB locale) | Gratuit | ~1ms | 95% pays | ❌ |
| **MaxMind GeoIP2** (API) | $0.001/req | ~20ms | 99% pays | ✅ |
| **IPInfo** | $0.001/req | ~15ms | 98% pays | ✅ |
| **IPQualityScore** | $0.001/req | ~25ms | 99% pays | ✅✅ |

---

## 🎯 Solution Recommandée : Approche Hybride

**Stratégie** : Combiner les deux approches pour maximiser les avantages.

### Architecture

```
┌─────────────┐
│  IP Address │
└──────┬──────┘
       │
       ├──────────────────────────────┐
       │                              │
       ▼                              ▼
┌──────────────┐            ┌──────────────────┐
│  Hash IP     │            │  GeoIP Lookup    │
│  (SHA-256)   │            │  (MaxMind Local) │
└──────┬───────┘            └────────┬─────────┘
       │                              │
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────┐
│          Features Stockées                    │
│  {                                            │
│    "ip_hash": "c775e7b757ede630",           │
│    "country": "FR",                          │
│    "region": "IDF",                          │
│    "asn": 3215,                              │
│    "is_vpn": false                           │
│  }                                            │
│  ⚠️ IP réelle JAMAIS stockée                │
└──────────────────────────────────────────────┘
```

### Implémentation

```python
import hashlib
import geoip2.database
from typing import Dict

class IPProcessor:
    def __init__(self):
        # Base de données locale (gratuite) de MaxMind
        self.geoip_reader = geoip2.database.Reader('GeoLite2-City.mmdb')
        self.asn_reader = geoip2.database.Reader('GeoLite2-ASN.mmdb')

    def process_ip(self, ip_address: str) -> Dict:
        """
        Traite l'IP et retourne des features anonymisées.
        L'IP réelle n'est jamais stockée.
        """
        # 1. Hash pour idempotence (velocity checks)
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]

        # 2. Extraction géographique (DB locale = ~1ms)
        try:
            geo_response = self.geoip_reader.city(ip_address)
            asn_response = self.asn_reader.asn(ip_address)

            features = {
                "ip_hash": ip_hash,  # Pour velocity checks
                "country": geo_response.country.iso_code,  # "FR"
                "country_name": geo_response.country.name,  # "France"
                "region": geo_response.subdivisions[0].iso_code if geo_response.subdivisions else None,
                "city": geo_response.city.name,
                "latitude": geo_response.location.latitude,
                "longitude": geo_response.location.longitude,
                "asn": asn_response.autonomous_system_number,
                "asn_org": asn_response.autonomous_system_organization,
                "is_eu": geo_response.country.is_in_european_union,
            }

            # 3. Vérification VPN/Proxy (optionnel, via API externe)
            # Pour MVP : skip (évite la latence)
            # Pour V1 : ajouter via IPQualityScore
            features["is_vpn"] = False  # TODO: Implémenter

            return features

        except Exception as e:
            # Fail gracefully : retourner features minimales
            return {
                "ip_hash": ip_hash,
                "country": "UNKNOWN",
                "is_vpn": False,
            }

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcule la distance en km entre deux coordonnées (formule Haversine)."""
        from math import radians, cos, sin, asin, sqrt

        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Rayon de la Terre en km
        return c * r
```

### Features ML Extraites

Les features suivantes sont **stockées** (pas l'IP) et utilisées par le modèle :

```python
{
    # Anonymisation
    "ip_hash": "c775e7b757ede630",  # Hash SHA-256 (16 chars)

    # Géographie
    "country": "FR",                 # Code pays ISO
    "region": "IDF",                 # Code région
    "city": "Paris",                 # Ville
    "latitude": 48.8566,
    "longitude": 2.3522,

    # Réseau
    "asn": 3215,                     # Orange France
    "asn_org": "Orange S.A.",

    # Risque
    "is_vpn": false,
    "is_proxy": false,
    "is_tor": false,
    "is_datacenter": false,

    # Calculs dérivés
    "distance_to_billing_address": 1250.5,  # km
    "country_mismatch": true,  # IP != pays carte
}
```

---

## Performance

### Latence

```
Opération                  | Latence
---------------------------|----------
Hash SHA-256               | ~0.1ms
GeoLite2 lookup (local DB) | ~1ms
ASN lookup (local DB)      | ~0.5ms
Total (sans VPN check)     | ~1.6ms
---------------------------|----------
Avec VPN API externe       | +15-25ms
```

**Conclusion** : La solution hybride avec DB locale ajoute **< 2ms** de latence, ce qui est négligeable pour notre objectif P95 < 100ms.

### Coût

```
Composant              | Coût
-----------------------|------
GeoLite2 (gratuit)     | 0€
MaxMind GeoIP2 (opt.)  | ~100€/mois pour 100k req/jour
IPQualityScore (opt.)  | ~100€/mois pour 100k req/jour
Total MVP              | 0€
Total V1 (avec VPN)    | ~200€/mois
```

---

## RGPD Compliance

### ✅ Conformité

1. **IP non stockée** : Seuls les features dérivées sont stockées
2. **Anonymisation** : Hash SHA-256 unidirectionnel
3. **Minimisation** : On ne collecte que ce qui est nécessaire (pays, région)
4. **Durée de rétention** : Features supprimées après 90 jours

### Justification Légale

**Base légale RGPD** : Intérêt légitime (Article 6.1.f)
- Prévention de la fraude = intérêt légitime de la banque
- Pas de stockage de l'IP complète = proportionné
- Features géographiques agrégées = anonymisation

**Documentation** :
- Mentionner dans la politique de confidentialité
- Droit d'accès : l'utilisateur peut demander ses features stockées
- Droit à l'oubli : suppression des features sur demande

---

## Plan de Déploiement

### Phase 1 : MVP (Semaine 1-2)
- ✅ Hash IP (SHA-256)
- ✅ GeoLite2 lookup (pays, région, ASN)
- ✅ Stockage features anonymisées
- ✅ Feature engineering (distance, country mismatch)

### Phase 2 : V1 (Semaine 3-4)
- ✅ Intégration IPQualityScore pour VPN/Proxy detection
- ✅ Cache Redis pour IPs fréquentes (réduire lookups)
- ✅ Monitoring de la précision géographique

### Phase 3 : V2 (Post-MVP)
- ✅ ML sur historique IP (behavioral patterns)
- ✅ Détection d'IP partagées (cafés, aéroports)
- ✅ Risk scoring par ASN

---

## Métriques de Succès

| Métrique | Objectif |
|----------|----------|
| Latence P95 (GeoIP lookup) | < 2ms |
| Précision géographique (pays) | > 95% |
| Amélioration AUC (avec features IP) | +0.02-0.04 |
| Taux de détection VPN | > 90% |

---

## Décision Finale

**Choix retenu** : **Approche Hybride**

**Justification** :
1. ✅ Performance : +1.6ms latence (négligeable)
2. ✅ RGPD : IP jamais stockée, features anonymisées
3. ✅ ML : Features riches (pays, ASN, distance) → meilleure précision
4. ✅ Coût : 0€ pour MVP (GeoLite2 gratuit)
5. ✅ Évolutivité : Possibilité d'ajouter VPN detection en V1

**Alternative rejetée** : Hash seul (trop peu d'informations pour le ML)

---

## Références

- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
- [RGPD - Article 6.1.f (Intérêt légitime)](https://gdpr.eu/article-6-how-to-process-personal-data-legally/)
- [CNIL - Adresses IP](https://www.cnil.fr/fr/definition/adresse-ip)
- [Stripe: IP Geolocation for Fraud Detection](https://stripe.com/docs/radar/rules/geography)
