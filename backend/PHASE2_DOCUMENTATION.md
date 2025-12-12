# Phase 2: Core Services - Implementation Guide

## Overview

Phase 2 implements three foundational services that support all subsequent phases:

1. **LocationService** - Geographic operations and Lebanon validation
2. **CacheManager** - Redis-based distributed caching
3. **QueryParser** - Natural language product query parsing

## Services Documentation

### 1. LocationService (`services/location.py`)

Handles all location-based operations with Lebanon-specific validation.

#### Key Features

- **Distance Calculation** - Haversine formula for accurate distances in km
- **Location Validation** - Lebanon bounds checking (33.0-34.7 lat, 35.1-36.6 lng)
- **Search Radius** - Bounding box calculation for API queries
- **City Lookup** - Predefined bounds for major Lebanese cities
- **Sorting** - Sort locations by distance from a center point

#### Main Methods

```python
# Calculate distance between two points (Haversine formula)
distance = LocationService.calculate_distance(
    {"lat": 33.8886, "lng": 35.4955},
    {"lat": 34.4325, "lng": 35.8455}
)
# Returns: 62.34 (km)

# Validate location is in Lebanon
is_valid = LocationService.validate_location(33.8886, 35.4955)
# Returns: True

# Get search radius bounds for Google Places API
bounds = LocationService.get_search_radius(
    {"lat": 33.8886, "lng": 35.4955},
    radius_km=10
)
# Returns: {"northeast": {...}, "southwest": {...}}

# Check if point is within radius
within = LocationService.is_within_radius(
    {"lat": 33.9, "lng": 35.5},
    {"lat": 33.8886, "lng": 35.4955},
    radius_km=10
)
# Returns: True

# Get predefined city bounds
beirut = LocationService.get_city_bounds("beirut")
# Returns: {"center": {...}, "radius": 15}

# Sort locations by distance
sorted_locs = LocationService.sort_by_distance(locations, center)
```

#### Usage Example

```python
from app.services.location import LocationService

# Validate user location
if not LocationService.validate_location(user_lat, user_lng):
    raise HTTPException(400, "Location must be in Lebanon")

# Calculate distance to store
store = {"lat": 33.89, "lng": 35.50}
user = {"lat": 33.88, "lng": 35.49}
distance = LocationService.calculate_distance(user, store)
print(f"Distance to store: {distance} km")

# Get search radius for store discovery
search_bounds = LocationService.get_search_radius(user, radius_km=10)
```

---

### 2. CacheManager (`services/cache.py`)

Redis-based caching with configurable TTLs and async support.

#### Key Features

- **Multi-tier Caching** - Different TTLs for different data types:
  - Stores: 24 hours (locations are stable)
  - Products: 6 hours (prices change frequently)
  - Full searches: 1 hour
- **Async Operations** - All methods are async-compatible
- **Pattern Matching** - Clear multiple keys with wildcard patterns
- **Connection Handling** - Graceful fallback if Redis unavailable
- **Stats Tracking** - Monitor cache usage and memory

#### TTL Configuration

Configured in `config.py`:
- `cache_ttl_stores_hours = 24`
- `cache_ttl_products_hours = 6`
- `cache_ttl_search_hours = 1`

#### Main Methods

```python
# Cache stores (24h TTL)
await cache.set_stores("stores:33.89:35.50:shoes", stores_list)
cached_stores = await cache.get_stores("stores:33.89:35.50:shoes")

# Cache products (6h TTL)
await cache.set_products("products:store_1:query_hash", products_list)
cached_products = await cache.get_products("products:store_1:query_hash")

# Cache search results (1h TTL)
await cache.set_search("33.89:35.50:adidas shoes", result_dict)
cached_search = await cache.get_search("33.89:35.50:adidas shoes")

# Generate cache keys
key = CacheManager.generate_key("stores", "33.89", "35.50", "shoes")
# Returns: "stores:33.89:35.50:shoes"

# Generate query hash
query_hash = CacheManager.generate_hash("adidas samba shoes")

# Delete specific key
await cache.delete("stores:33.89:35.50:shoes")

# Clear by pattern
deleted_count = await cache.clear_by_pattern("products:store_1:*")

# Get cache statistics
stats = await cache.get_stats()
# Returns: {"used_memory": "2.5M", "connected_clients": 1, ...}
```

#### Usage Example

```python
from app.services.cache import CacheManager

cache = CacheManager()

async def search_stores(location, category):
    # Generate cache key
    key = CacheManager.generate_key(
        "stores",
        str(location["lat"]),
        str(location["lng"]),
        category
    )

    # Check cache first
    cached = await cache.get_stores(key)
    if cached:
        return cached

    # Fetch from API and cache
    stores = await discover_stores(location, category)
    await cache.set_stores(key, stores)

    return stores
```

#### Cache Key Naming Convention

```
stores:{lat}:{lng}:{category}
products:{store_id}:{query_hash}
search:{lat}:{lng}:{query_hash}
```

---

### 3. QueryParser (`services/query_parser.py`)

Natural language product query parser using regex patterns and rule-based extraction.

#### Key Features

- **Component Extraction** - Brand, model, category, size, gender, color
- **Flexible Matching** - Handles various query formats
- **Category Detection** - Maps to predefined categories (shoes, clothing, electronics, accessories)
- **Gender Normalization** - Converts variants (men/man, women/woman)
- **Search Optimization** - Builds optimized search terms from parsed data

#### Supported Brands (Extensible)

```
Nike, Adidas, Puma, Reebok, New Balance, Converse,
Gucci, Louis Vuitton, Chanel, Dior, Prada,
Apple, Samsung, Sony, LG, Philips
```

#### Supported Categories

- **shoes** - shoe, sneaker, boot, sandal, slipper, pump
- **clothing** - shirt, t-shirt, pants, jeans, dress, jacket, coat
- **electronics** - phone, laptop, headphone, earphone, tablet, camera
- **accessories** - bag, wallet, watch, belt, scarf, hat

#### Main Methods

```python
# Parse full query
parsed = QueryParser.parse("adidas samba man 42 black")
# Returns: ParsedQuery(
#   brand="Adidas",
#   model="Samba",
#   category="shoes",
#   size="42",
#   gender="men",
#   color="black",
#   original_query="adidas samba man 42 black"
# )

# Build optimized search terms
search_terms = QueryParser.build_search_terms(parsed)
# Returns: "Adidas Samba black 42"

# Get fallback category
category = QueryParser.get_fallback_category("nike shoe")
# Returns: "shoes"

# Normalize query
normalized = QueryParser.normalize_query("  ADIDAS   SAMBA  ")
# Returns: "adidas samba"
```

#### Component Extraction Methods

```python
# Extract individual components
brand = QueryParser._extract_brand("adidas samba")         # "Adidas"
category = QueryParser._extract_category("shoe")           # "shoes"
gender = QueryParser._extract_gender("men")                # "men"
color = QueryParser._extract_color("black")                # "black"
size = QueryParser._extract_size("size 42", "shoes")       # "42"
model = QueryParser._extract_model("adidas samba", "Adidas") # "samba"
```

#### Usage Example

```python
from app.services.query_parser import QueryParser
from app.services.location import LocationService

async def search_products(query: str, location: dict):
    # Validate location
    if not LocationService.validate_location(**location):
        raise HTTPException(400, "Invalid location")

    # Parse query
    parsed = QueryParser.parse(query)

    # Use parsed components for search
    if parsed.category:
        category = parsed.category
    else:
        category = QueryParser.get_fallback_category(query)

    # Build optimized search terms
    search_terms = QueryParser.build_search_terms(parsed)

    # Use for subsequent agents
    return {
        "parsed_query": parsed,
        "search_category": category,
        "search_terms": search_terms
    }
```

#### Query Examples and Parsing Results

```
Input: "adidas samba man 42 black"
Output: brand="Adidas", model="Samba", size="42", gender="men", color="black"

Input: "nike air max women"
Output: brand="Nike", model="air max", gender="women"

Input: "samsung phone 256gb"
Output: brand="Samsung", category="electronics", model="phone"

Input: "red gucci bag"
Output: brand="Gucci", category="accessories", color="red"

Input: "size 8 white sneaker"
Output: category="shoes", size="8", color="white"
```

---

## Testing

Comprehensive test suite in `tests/test_services.py`:

```bash
# Run all tests
pytest tests/test_services.py -v

# Run specific test class
pytest tests/test_services.py::TestLocationService -v

# Run with coverage
pytest tests/test_services.py --cov=app.services
```

### Test Classes

1. **TestLocationService** - 14 tests covering distance calculation, validation, bounds
2. **TestCacheManager** - Async tests for caching operations (requires Redis)
3. **TestQueryParser** - 17 tests for query parsing and extraction

### Sample Test Execution

```bash
# Location Service tests
pytest tests/test_services.py::TestLocationService -v
# Output: 14 passed

# Query Parser tests
pytest tests/test_services.py::TestQueryParser -v
# Output: 17 passed

# Cache tests (requires Redis)
pytest tests/test_services.py::TestCacheManager -v
# Output: skipped if Redis unavailable
```

---

## Integration with FastAPI

### Example: Complete Search Flow

```python
from fastapi import FastAPI, HTTPException
from app.services.location import LocationService
from app.services.cache import CacheManager
from app.services.query_parser import QueryParser

app = FastAPI()
cache = CacheManager()

@app.post("/api/search")
async def search_products(query: str, location: dict):
    # Validate location
    if not LocationService.validate_location(**location):
        raise HTTPException(400, "Location must be in Lebanon")

    # Check cache
    cache_key = CacheManager.generate_key(
        str(location["lat"]),
        str(location["lng"]),
        query
    )
    cached_result = await cache.get_search(cache_key)
    if cached_result:
        return {**cached_result, "cached": True}

    # Parse query
    parsed_query = QueryParser.parse(query)

    # Get search bounds
    search_radius = LocationService.get_search_radius(location, radius_km=10)

    # Discover stores (Phase 3)
    stores = await discover_stores(location, parsed_query.category)

    # Cache stores
    store_cache_key = CacheManager.generate_key(
        "stores",
        str(location["lat"]),
        str(location["lng"]),
        parsed_query.category or "general"
    )
    await cache.set_stores(store_cache_key, stores)

    # Continue with scraping and analysis...

    # Cache final result
    await cache.set_search(cache_key, result)

    return result
```

---

## Configuration

Core settings in `config.py`:

```python
# Location validation
min_latitude: float = 33.0
max_latitude: float = 34.7
min_longitude: float = 35.1
max_longitude: float = 36.6

# Cache TTLs
cache_ttl_stores_hours: int = 24
cache_ttl_products_hours: int = 6
cache_ttl_search_hours: int = 1

# Location service
store_search_radius_km: int = 10
min_store_rating: float = 3.5
```

---

## Ready for Phase 3

Phase 2 provides the foundation for:
- **Phase 3**: Store Discovery Agent using location service
- **Phase 4**: Scraper Agent with caching
- **Phase 5**: RAG Agent with embeddings
- **Phase 6**: Analysis Agent with LLM
- **Phase 7**: LangGraph workflow orchestration

## Next Steps

1. Phase 3 will implement `StoreDiscoveryAgent` using Google Places API
2. Use `LocationService` for validation and distance calculations
3. Use `CacheManager` to cache store discovery results
4. Use `QueryParser` to determine search categories
