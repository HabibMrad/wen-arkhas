# Phase 2 Quick Start Guide

## Installation & Setup

```bash
# 1. Navigate to backend directory
cd wen-arkhas/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 5. Start Redis (required for caching)
redis-server  # Or use Docker: docker run -p 6379:6379 redis
```

## Testing Core Services

```bash
# Run all Phase 2 tests
pytest tests/test_services.py -v

# Run specific service tests
pytest tests/test_services.py::TestLocationService -v
pytest tests/test_services.py::TestQueryParser -v
pytest tests/test_services.py::TestCacheManager -v

# Test with coverage report
pytest tests/test_services.py --cov=app.services --cov-report=html
```

## Using the Services

### LocationService

```python
from app.services.location import LocationService

# Validate user is in Lebanon
if LocationService.validate_location(33.8886, 35.4955):
    print("Location valid")

# Calculate distance between two points
distance = LocationService.calculate_distance(
    {"lat": 33.8886, "lng": 35.4955},
    {"lat": 34.4325, "lng": 35.8455}
)
print(f"Distance: {distance} km")

# Get search radius for store discovery
bounds = LocationService.get_search_radius(
    {"lat": 33.8886, "lng": 35.4955},
    radius_km=10
)

# Sort stores by distance
stores = LocationService.sort_by_distance(stores, user_location)
```

### QueryParser

```python
from app.services.query_parser import QueryParser

# Parse user query
query = "adidas samba man 42 black"
parsed = QueryParser.parse(query)

print(f"Brand: {parsed.brand}")          # Adidas
print(f"Model: {parsed.model}")          # Samba
print(f"Size: {parsed.size}")            # 42
print(f"Gender: {parsed.gender}")        # men
print(f"Color: {parsed.color}")          # black

# Build search terms
search_terms = QueryParser.build_search_terms(parsed)
print(f"Search: {search_terms}")         # Adidas Samba black 42

# Get fallback category if not detected
category = QueryParser.get_fallback_category(query)
```

### CacheManager

```python
import asyncio
from app.services.cache import CacheManager

cache = CacheManager()

async def demo():
    # Cache stores
    key = CacheManager.generate_key("stores", "33.89", "35.50", "shoes")
    stores = [{"id": 1, "name": "Store A"}]

    await cache.set_stores(key, stores)
    cached = await cache.get_stores(key)
    print(f"Cached stores: {cached}")

    # Cache products
    prod_key = CacheManager.generate_key("products", "store_1", "query_hash")
    products = [{"id": "p1", "title": "Product"}]

    await cache.set_products(prod_key, products)

    # Cache full search
    search_key = CacheManager.generate_key("33.89", "35.50", "query")
    result = {"stores_found": 5, "products_found": 20}

    await cache.set_search(search_key, result)

asyncio.run(demo())
```

## Running the API Server

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test health endpoint
curl http://localhost:8000/health

# Output:
# {"status":"healthy","version":"0.1.0"}
```

## Debugging Tips

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### Test LocationService Distance Calculation

```python
from app.services.location import LocationService

# Test with known cities
beirut = {"lat": 33.8886, "lng": 35.4955}
tripoli = {"lat": 34.4325, "lng": 35.8455}

distance = LocationService.calculate_distance(beirut, tripoli)
print(f"Beirut to Tripoli: {distance} km")  # Should be ~62 km
```

### Check Redis Connection

```python
from app.services.cache import CacheManager

cache = CacheManager()
if cache._is_connected():
    print("Redis connected")
else:
    print("Redis not available - cache disabled")
```

### Debug Query Parsing

```python
from app.services.query_parser import QueryParser

queries = [
    "adidas samba man 42",
    "nike air max women size 8",
    "samsung phone 256gb",
]

for query in queries:
    parsed = QueryParser.parse(query)
    print(f"Query: {query}")
    print(f"  Brand: {parsed.brand}")
    print(f"  Category: {parsed.category}")
    print(f"  Model: {parsed.model}")
    print()
```

## Common Issues

### Redis Connection Failed

```
Error: Failed to connect to Redis
Solution:
1. Ensure Redis is running: redis-server
2. Check Redis URL in .env: REDIS_URL=redis://localhost:6379
3. Verify Redis port: redis-cli ping
```

### Import Errors

```
Error: ModuleNotFoundError: No module named 'app'
Solution:
1. Ensure you're in the backend directory
2. PYTHONPATH=. pytest tests/test_services.py
3. Or set up proper imports in conftest.py
```

### Test Failures

```
Error: Some tests fail with Redis tests
Solution:
Tests that require Redis will skip if Redis is unavailable
Use: pytest tests/test_services.py -v --capture=no
```

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── location.py      # LocationService
│   │   ├── cache.py         # CacheManager
│   │   ├── query_parser.py  # QueryParser
│   │   └── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   └── models/
│       └── schemas.py       # Pydantic models
├── tests/
│   ├── test_services.py     # Phase 2 tests
│   └── __init__.py
├── conftest.py              # Pytest config
├── requirements.txt         # Dependencies
├── PHASE2_DOCUMENTATION.md  # Detailed docs
└── QUICK_START.md          # This file
```

## Next: Phase 3

Phase 3 will implement store discovery using:
- `LocationService.get_search_radius()` - Get bounds for API
- `QueryParser.parse()` - Extract search category
- `CacheManager.set_stores()` - Cache discovered stores
- Google Places API - Find nearby stores

Ready to start Phase 3? The foundation is solid!
