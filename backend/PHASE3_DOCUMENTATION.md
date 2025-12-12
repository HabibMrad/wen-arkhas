# Phase 3: Store Discovery - Implementation Guide

## Overview

Phase 3 implements the first two LangGraph agent nodes:

1. **QueryParserAgent** - Parse user queries into structured components
2. **StoreDiscoveryAgent** - Find nearby stores using Google Places API

Together, these agents form the foundation of the multi-agent system.

## QueryParserAgent

### Purpose
Parse natural language product queries into structured components that other agents can process.

### Architecture
```
Input: SearchState with 'query' field
  ↓
Parse query using QueryParser service
  ↓
Output: SearchState with 'parsed_query' field populated
```

### Implementation Details

**File:** `app/agents/query_parser.py`

**Key Methods:**

```python
# Main execution method
QueryParserAgent.execute(state: Dict[str, Any]) -> Dict[str, Any]
    # Parses the query and populates parsed_query in state
    # Tracks execution time in state["execution_time_ms"]["parse_query"]

# Validate parsing was successful
QueryParserAgent.validate_output(state: Dict[str, Any]) -> bool
    # Returns True if parsed_query is valid

# Get search category for store discovery
QueryParserAgent.get_search_category(state: Dict[str, Any]) -> str
    # Returns category: "shoes", "clothing", "electronics", "accessories", or "general"

# Build optimized search terms for web scraping
QueryParserAgent.get_search_terms(state: Dict[str, Any]) -> str
    # Returns optimized search string combining brand, model, color, size
```

### Usage Example

```python
from app.agents.query_parser import QueryParserAgent

# Create initial state
state = {
    "query": "adidas samba man 42 black",
    "location": {"lat": 33.8886, "lng": 35.4955},
    "errors": [],
    "execution_time_ms": {},
}

# Execute agent
result = QueryParserAgent.execute(state)

# Access results
print(result["parsed_query"].brand)    # "Adidas"
print(result["parsed_query"].model)    # "Samba"
print(result["parsed_query"].size)     # "42"
print(result["parsed_query"].gender)   # "men"
print(result["parsed_query"].color)    # "black"
print(result["execution_time_ms"])     # {"parse_query": 5}
```

### Output Format

```python
ParsedQuery(
    brand: Optional[str],              # e.g., "Adidas"
    model: Optional[str],              # e.g., "Samba"
    category: Optional[str],           # e.g., "shoes"
    size: Optional[str],               # e.g., "42"
    gender: Optional[str],             # e.g., "men", "women"
    color: Optional[str],              # e.g., "black"
    original_query: str                # Original user query
)
```

### Integration with LangGraph

```python
from app.agents.query_parser import parse_query_node

workflow.add_node("parse_query", parse_query_node)
workflow.set_entry_point("parse_query")
workflow.add_edge("parse_query", "discover_stores")
```

---

## StoreDiscoveryAgent

### Purpose
Find nearby retail stores using Google Places API and cache results for efficiency.

### Architecture
```
Input: SearchState with 'location', 'parsed_query'
  ↓
Validate location (must be in Lebanon)
  ↓
Check Redis cache (24h TTL)
  ↓
If cache miss:
  Query Google Places API
  Filter by rating and distance
  Calculate distances
  Cache results
  ↓
Output: SearchState with 'stores' field populated
```

### Implementation Details

**File:** `app/agents/store_discovery.py`

**Key Methods:**

```python
# Main execution method (async)
async StoreDiscoveryAgent.execute(state: Dict[str, Any]) -> Dict[str, Any]
    # Discovers stores and populates state["stores"]
    # Returns cached results or queries Google Places API
    # Tracks execution time in state["execution_time_ms"]["discover_stores"]

# Discover stores via Google Places API
async StoreDiscoveryAgent._discover_stores(
    location: Dict[str, float],
    category: str
) -> List[StoreModel]
    # Queries Google Places API
    # Handles pagination
    # Respects rate limiting (2s between pages)

# Parse Google Places result
StoreDiscoveryAgent._parse_place_result(
    place: Dict[str, Any],
    user_location: Dict[str, float]
) -> Optional[StoreModel]
    # Converts API result to StoreModel
    # Calculates distance from user

# Validate store meets criteria
StoreDiscoveryAgent._is_valid_store(store: StoreModel) -> bool
    # Checks minimum rating (default: 3.5)
    # Checks distance (default: 10km radius)

# Build search query for Google Places
StoreDiscoveryAgent._build_search_query(category: str) -> str
    # Returns appropriate search keyword for category
```

### Usage Example

```python
from app.agents.store_discovery import StoreDiscoveryAgent
import asyncio

async def discover():
    # Create agent
    agent = StoreDiscoveryAgent()

    # Create state
    state = {
        "query": "adidas shoes",
        "location": {"lat": 33.8886, "lng": 35.4955},
        "parsed_query": ParsedQuery(
            brand="Adidas",
            category="shoes",
            original_query="adidas shoes"
        ),
        "errors": [],
        "execution_time_ms": {},
    }

    # Execute
    result = await agent.execute(state)

    # Access results
    for store in result["stores"]:
        print(f"{store.name} - {store.distance_km}km away")

asyncio.run(discover())
```

### Output Format

```python
StoreModel(
    store_id: str,                     # Google Place ID
    name: str,                         # Store name
    address: str,                      # Full address
    lat: float,                        # Latitude
    lng: float,                        # Longitude
    distance_km: float,                # Distance from user
    website: Optional[str],            # Store website (requires details API)
    phone: Optional[str],              # Store phone (requires details API)
    rating: float,                     # Google rating (0-5)
    reviews_count: int,                # Number of reviews
    currently_open: bool               # Is store currently open
)
```

### Cache Strategy

**Cache Key:** `stores:{lat}:{lng}:{category}`

**TTL:** 24 hours (stores/malls don't move)

**When Cached:**
```python
# Cache after successful store discovery
cache_key = CacheManager.generate_key(
    "stores",
    str(location["lat"]),
    str(location["lng"]),
    category
)
await cache.set_stores(cache_key, store_dicts, ttl_hours=24)
```

**When Retrieved:**
```python
# Check cache before API call
cached_stores = await cache.get_stores(cache_key)
if cached_stores:
    return [StoreModel(**s) for s in cached_stores]
```

### Google Places API Integration

**Configuration:**
```python
# In config.py
GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY")

# In .env
GOOGLE_PLACES_API_KEY=your-api-key-here
```

**API Calls:**

1. **places_nearby** - Find stores in radius
   - Location: User coordinates
   - Radius: 10km (configurable)
   - Keyword: Category-specific (shoes, electronics, etc.)
   - Type: store

2. **Rate Limiting**
   - Max 1 request/second per domain
   - 2-second delay between paginated results
   - Respects Google's quotas

### Error Handling

Gracefully handles:
- Missing Google Places API key
- Invalid location (outside Lebanon)
- API rate limits
- Network timeouts
- Invalid place results

All errors are accumulated in `state["errors"]` without stopping execution.

### Integration with LangGraph

```python
from app.agents.store_discovery import discover_stores_node

workflow.add_node("discover_stores", discover_stores_node)
workflow.add_edge("parse_query", "discover_stores")

# Optional: Add retry logic if too few stores found
workflow.add_conditional_edges(
    "discover_stores",
    lambda state: "retry" if len(state["stores"]) < 3 else "continue",
    {"retry": "discover_stores", "continue": "next_node"}
)
```

---

## LangGraph Workflow (Phase 3)

### Workflow Definition

**File:** `app/graph/workflow.py`

**Current Flow (Phase 3):**
```
parse_query → discover_stores → END
```

**Future Flow (after Phase 4-6):**
```
parse_query → discover_stores → scrape_products →
match_products → analyze → END
```

### Build Workflow

```python
from app.graph.workflow import WorkflowBuilder, WorkflowExecutor

# Build Phase 3 workflow
graph = WorkflowBuilder.build_phase3_workflow()

# Create executor
executor = WorkflowExecutor(graph)

# Execute
result = await executor.invoke(
    query="adidas samba man 42",
    location={"lat": 33.8886, "lng": 35.4955}
)

print(f"Found {len(result['stores'])} stores")
print(f"Execution times: {result['execution_time_ms']}")
```

### Streaming Execution

For real-time progress updates:

```python
# Stream workflow execution
async for event in executor.invoke_streaming(
    query="adidas shoes",
    location={"lat": 33.8886, "lng": 35.4955}
):
    print(f"Status: {event['status']}")
    print(f"Node: {event.get('node')}")
    print(f"Data: {event.get('data')}")
```

### State Flow

```python
SearchState {
    # Input
    query: "adidas samba man 42",
    location: {"lat": 33.8886, "lng": 35.4955},

    # After parse_query node
    parsed_query: ParsedQuery(...),

    # After discover_stores node
    stores: [StoreModel(...), ...],

    # Metadata
    errors: [],
    execution_time_ms: {
        "parse_query": 5,
        "discover_stores": 1240
    }
}
```

---

## Testing Phase 3

**Test File:** `tests/test_agents_phase3.py`

### Running Tests

```bash
# All Phase 3 tests
pytest tests/test_agents_phase3.py -v

# QueryParserAgent tests
pytest tests/test_agents_phase3.py::TestQueryParserAgent -v

# StoreDiscoveryAgent tests
pytest tests/test_agents_phase3.py::TestStoreDiscoveryAgent -v

# Integration tests
pytest tests/test_agents_phase3.py::TestIntegration -v

# With coverage
pytest tests/test_agents_phase3.py --cov=app.agents
```

### Test Coverage

**QueryParserAgent (9 tests):**
- Valid query parsing
- Empty query handling
- Minimal query parsing
- Output validation
- Category extraction
- Search term building
- Async node function

**StoreDiscoveryAgent (11 tests):**
- Client initialization
- Invalid location handling
- Out of bounds location
- Google Places result parsing
- Store validation (rating, distance)
- Search query building
- Error handling

**Integration Tests (4 tests):**
- Complete Phase 3 workflow
- Error accumulation
- Execution time tracking
- State flow validation

### Key Test Patterns

```python
# Mock Google Maps client
@patch("app.agents.store_discovery.googlemaps.Client")
def test_something(mock_client_class):
    agent = StoreDiscoveryAgent()
    # Test without actual API calls

# Test async functions
@pytest.mark.asyncio
async def test_async_execution():
    result = await agent.execute(state)
    assert result is not None

# Verify state structure
def test_state_flow():
    state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})
    assert validate_state(state) is True
```

---

## Configuration

**Location Service Settings** (`config.py`):
```python
# Lebanon bounds
min_latitude: float = 33.0
max_latitude: float = 34.7
min_longitude: float = 35.1
max_longitude: float = 36.6

# Store discovery
store_search_radius_km: int = 10
max_stores_per_search: int = 10
min_store_rating: float = 3.5

# Cache
cache_ttl_stores_hours: int = 24
```

**Environment Variables** (`.env`):
```
GOOGLE_PLACES_API_KEY=your-api-key-here
REDIS_URL=redis://localhost:6379
```

---

## Performance Characteristics

### Execution Times

**QueryParserAgent:**
- Typical: 1-5ms
- Max: ~10ms
- Bottleneck: Regex pattern matching

**StoreDiscoveryAgent:**
- Cache hit: 10-20ms
- API call: 800-1500ms (depends on network)
- Pagination: +2s per page
- Bottleneck: Google Places API latency

### Cache Benefits

**Without Cache:**
- Each search: ~1000-2000ms (API call)

**With Cache:**
- First search: ~1000-2000ms (cache miss)
- Subsequent searches (same location): ~20-30ms (cache hit)
- 24-hour cache reduces API costs by 95%+

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now see detailed logs
# [DEBUG] QueryParserAgent: Brand found: Nike
# [DEBUG] StoreDiscoveryAgent: Cache hit: 5 stores
```

### Test with Specific Location

```python
# Test Beirut
location = {"lat": 33.8886, "lng": 35.4955}

# Test Tripoli
location = {"lat": 34.4325, "lng": 35.8455}

# Test Sidon
location = {"lat": 33.5597, "lng": 35.3724}
```

### Validate Google Places API

```python
# Test API key is valid
import googlemaps
gmaps = googlemaps.Client(key=YOUR_API_KEY)
result = gmaps.places_nearby(location=(33.8886, 35.4955), radius=1000)
print(result)
```

### Check Cache

```python
from app.services.cache import CacheManager

cache = CacheManager()
stats = await cache.get_stats()
print(f"Cache memory: {stats['used_memory']}")
print(f"Connected clients: {stats['connected_clients']}")
```

---

## Common Issues

### Google Places API Key Not Working

```
Error: "Invalid API key provided"
Solution:
1. Verify key in .env: GOOGLE_PLACES_API_KEY=sk_...
2. Check key is enabled in Google Cloud Console
3. Verify "Places API" is enabled in project
4. Check quota limits aren't exceeded
```

### Stores Not Found

```
Error: "No stores found for category: shoes"
Possible causes:
1. Wrong location (outside search radius)
2. Category not recognized (check fallback)
3. API key quota exhausted
4. No retail stores near location
Solution: Check logs for details, verify location is valid
```

### Cache Not Working

```
Error: "Redis connection failed"
Solution:
1. Start Redis: redis-server
2. Verify REDIS_URL in .env
3. Check Redis is running: redis-cli ping
4. Caching will be disabled, operations will still work
```

---

## Ready for Phase 4

Phase 3 provides:
- ✅ Query parsing with 30+ brands
- ✅ Store discovery with Google Places
- ✅ Redis caching for performance
- ✅ Distance calculations
- ✅ Error handling and logging

Phase 4 (Scraping) will use:
- `QueryParser.build_search_terms()` for search
- `CacheManager` to cache products
- Store data to determine scraping targets

---

## Next Steps

1. Implement Phase 4: ScraperAgent
   - Use Playwright for JavaScript sites
   - Use BeautifulSoup for static HTML
   - Respect rate limiting (1 req/sec per domain)
   - Cache products (6h TTL)

2. Implement Phase 5: RAGAgent
   - Embed products with sentence-transformers
   - Store in Pinecone vector database
   - Perform semantic matching

3. Implement Phase 6: AnalysisAgent
   - Use OpenRouter API (Claude Sonnet 4)
   - Analyze and recommend products

4. Complete LangGraph workflow
   - Connect all 5 agents
   - Add conditional retry logic
   - Streaming execution for progress updates
