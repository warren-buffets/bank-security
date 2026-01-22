"""
IP Geolocation module using ip-api.com (free, no API key required).
Rate limit: 45 requests/minute - suitable for MVP.
Includes Redis caching to avoid repeated lookups.
Prometheus metrics for monitoring cache efficiency and geographic distribution.
"""
import json
import logging
import os
import time
import httpx
import redis
from typing import Optional
from dataclasses import dataclass, asdict
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

# Cache metrics
GEO_CACHE_HITS = Counter(
    "geolocation_cache_hits_total",
    "Total number of geolocation cache hits"
)
GEO_CACHE_MISSES = Counter(
    "geolocation_cache_misses_total",
    "Total number of geolocation cache misses"
)

# API call metrics
GEO_API_CALLS = Counter(
    "geolocation_api_calls_total",
    "Total number of calls to ip-api.com",
    ["status"]  # success, error, timeout
)
GEO_API_LATENCY = Histogram(
    "geolocation_api_latency_seconds",
    "Latency of ip-api.com API calls",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# Geographic distribution metrics
GEO_COUNTRY_REQUESTS = Counter(
    "geolocation_country_requests_total",
    "Number of geolocated requests by country",
    ["country"]
)
GEO_PRIVATE_IP_SKIPPED = Counter(
    "geolocation_private_ip_skipped_total",
    "Number of private/local IPs skipped"
)

# Cache size metric (updated periodically)
GEO_CACHE_SIZE = Gauge(
    "geolocation_cache_size",
    "Current number of cached IP geolocations"
)

IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,lat,lon,city,regionName,country,isp,org,as,query"

# Redis cache settings (from environment or defaults)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = 1  # Use separate DB for geolocation cache
CACHE_TTL_SECONDS = 86400  # 24 hours

# Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client for caching."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis cache at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}")
            _redis_client = None
    return _redis_client


def cache_key(ip: str) -> str:
    """Generate cache key for IP address."""
    return f"geo:ip:{ip}"


@dataclass
class GeoLocation:
    """Geolocation data from IP lookup."""
    ip: str
    lat: float
    lon: float
    city: str
    region: str
    country: str
    city_pop: int  # Estimated from city size
    success: bool
    error: Optional[str] = None


# City population estimates (rough approximations for common cities)
# In production, use a proper database like GeoNames
CITY_POPULATION_ESTIMATES = {
    # France
    "paris": 2_161_000,
    "marseille": 861_000,
    "lyon": 513_000,
    "toulouse": 471_000,
    "nice": 342_000,
    "nantes": 303_000,
    "strasbourg": 277_000,
    "montpellier": 277_000,
    "bordeaux": 249_000,
    "lille": 232_000,
    # USA
    "new york": 8_336_000,
    "los angeles": 3_979_000,
    "chicago": 2_693_000,
    "houston": 2_320_000,
    "phoenix": 1_680_000,
    "san francisco": 873_000,
    "seattle": 737_000,
    "boston": 692_000,
    "miami": 467_000,
    # UK
    "london": 8_982_000,
    "birmingham": 1_141_000,
    "manchester": 547_000,
    # Germany
    "berlin": 3_645_000,
    "munich": 1_472_000,
    "frankfurt": 753_000,
    # Default for unknown cities
    "default_large": 500_000,
    "default_medium": 100_000,
    "default_small": 20_000,
}


def estimate_city_population(city: str, country: str) -> int:
    """
    Estimate city population based on city name.
    In production, use GeoNames database for accurate data.
    """
    if not city:
        return CITY_POPULATION_ESTIMATES["default_medium"]

    city_lower = city.lower()

    # Direct lookup
    if city_lower in CITY_POPULATION_ESTIMATES:
        return CITY_POPULATION_ESTIMATES[city_lower]

    # Capital cities tend to be larger
    capitals = ["paris", "london", "berlin", "madrid", "rome", "washington", "tokyo", "beijing"]
    if city_lower in capitals:
        return CITY_POPULATION_ESTIMATES["default_large"]

    # Default based on country development
    developed_countries = ["US", "GB", "DE", "FR", "JP", "CA", "AU", "NL", "BE", "CH"]
    if country in developed_countries:
        return CITY_POPULATION_ESTIMATES["default_medium"]

    return CITY_POPULATION_ESTIMATES["default_small"]


def _geo_to_cache(geo: GeoLocation) -> str:
    """Serialize GeoLocation to JSON for cache storage."""
    return json.dumps(asdict(geo))


def _geo_from_cache(data: str) -> GeoLocation:
    """Deserialize GeoLocation from cache JSON."""
    d = json.loads(data)
    return GeoLocation(**d)


async def geolocate_ip(ip: str, timeout: float = 2.0) -> GeoLocation:
    """
    Get geolocation data for an IP address using ip-api.com.
    Results are cached in Redis for 24 hours.

    Args:
        ip: IP address to lookup
        timeout: Request timeout in seconds

    Returns:
        GeoLocation object with coordinates and city info
    """
    # Skip private/local IPs
    if ip.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                      "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                      "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                      "172.30.", "172.31.", "192.168.", "127.", "0.")):
        logger.debug(f"Skipping private IP: {ip}")
        GEO_PRIVATE_IP_SKIPPED.inc()
        return GeoLocation(
            ip=ip,
            lat=48.8566,  # Default to Paris
            lon=2.3522,
            city="Paris",
            region="Île-de-France",
            country="FR",
            city_pop=2_161_000,
            success=False,
            error="Private IP address"
        )

    # Try to get from cache first
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached = redis_client.get(cache_key(ip))
            if cached:
                geo = _geo_from_cache(cached)
                logger.info(f"Cache HIT for IP {ip} -> {geo.city}")
                GEO_CACHE_HITS.inc()
                if geo.country:
                    GEO_COUNTRY_REQUESTS.labels(country=geo.country).inc()
                return geo
            else:
                GEO_CACHE_MISSES.inc()
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
            GEO_CACHE_MISSES.inc()

    # Not in cache, fetch from API
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(IP_API_URL.format(ip=ip))
            data = response.json()

            # Record API latency
            api_latency = time.time() - start_time
            GEO_API_LATENCY.observe(api_latency)

            if data.get("status") == "success":
                city = data.get("city", "")
                country = data.get("country", "")

                geo = GeoLocation(
                    ip=ip,
                    lat=data.get("lat", 0.0),
                    lon=data.get("lon", 0.0),
                    city=city,
                    region=data.get("regionName", ""),
                    country=country,
                    city_pop=estimate_city_population(city, country),
                    success=True
                )
                logger.info(f"Geolocated {ip} -> {geo.city}, {geo.country} ({geo.lat}, {geo.lon})")

                # Record metrics
                GEO_API_CALLS.labels(status="success").inc()
                if country:
                    GEO_COUNTRY_REQUESTS.labels(country=country).inc()

                # Store in cache
                if redis_client:
                    try:
                        redis_client.setex(cache_key(ip), CACHE_TTL_SECONDS, _geo_to_cache(geo))
                        logger.debug(f"Cached geolocation for {ip}")
                        # Update cache size metric
                        _update_cache_size(redis_client)
                    except Exception as e:
                        logger.warning(f"Redis cache write error: {e}")

                return geo
            else:
                error_msg = data.get("message", "Unknown error")
                logger.warning(f"IP geolocation failed for {ip}: {error_msg}")
                GEO_API_CALLS.labels(status="error").inc()
                return GeoLocation(
                    ip=ip,
                    lat=0.0,
                    lon=0.0,
                    city="",
                    region="",
                    country="",
                    city_pop=CITY_POPULATION_ESTIMATES["default_medium"],
                    success=False,
                    error=error_msg
                )

    except httpx.TimeoutException:
        logger.warning(f"IP geolocation timeout for {ip}")
        GEO_API_CALLS.labels(status="timeout").inc()
        GEO_API_LATENCY.observe(time.time() - start_time)
        return GeoLocation(
            ip=ip,
            lat=0.0,
            lon=0.0,
            city="",
            region="",
            country="",
            city_pop=CITY_POPULATION_ESTIMATES["default_medium"],
            success=False,
            error="Timeout"
        )
    except Exception as e:
        logger.error(f"IP geolocation error for {ip}: {e}")
        GEO_API_CALLS.labels(status="error").inc()
        GEO_API_LATENCY.observe(time.time() - start_time)
        return GeoLocation(
            ip=ip,
            lat=0.0,
            lon=0.0,
            city="",
            region="",
            country="",
            city_pop=CITY_POPULATION_ESTIMATES["default_medium"],
            success=False,
            error=str(e)
        )


def _update_cache_size(redis_client: redis.Redis) -> None:
    """Update the cache size gauge metric (called periodically)."""
    try:
        # Count keys matching geo:ip:* pattern
        cursor = 0
        count = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match="geo:ip:*", count=100)
            count += len(keys)
            if cursor == 0:
                break
        GEO_CACHE_SIZE.set(count)
    except Exception as e:
        logger.debug(f"Could not update cache size metric: {e}")
