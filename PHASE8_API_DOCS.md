# Phase 8 API Documentation - FastAPI Endpoints

Complete REST API for Wen-Arkhas price comparison platform.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently no authentication required. Will be added in future phases.

---

## Endpoints

### 1. Health Check

**GET `/health`**

Check if the API service is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-12-10T12:34:56.789Z"
}
```

**Status Code:** 200 (OK)

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 2. Search Products (Standard)

**POST `/api/search`**

Execute a complete product search with all 5 agents. Returns final results after workflow completes.

**Request Body:**
```json
{
  "query": "adidas Samba man 42",
  "location": {
    "lat": 33.89,
    "lng": 35.50
  }
}
```

**Parameters:**
- `query` (string, required): Product search query (1-500 chars)
  - Examples: "nike shoes", "adidas samba 42", "iphone 15 pro"
- `location.lat` (float, required): Latitude (-90 to 90)
- `location.lng` (float, required): Longitude (-180 to 180)
  - Must be within Lebanon boundaries

**Response (Success):**
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "adidas Samba man 42",
  "location": {
    "lat": 33.89,
    "lng": 35.50,
    "address": null
  },
  "stores_found": 5,
  "products_found": 12,
  "results": [
    {
      "product_id": "p1",
      "store_id": "s1",
      "title": "Adidas Samba OG",
      "price": 99.99,
      "currency": "USD",
      "rating": 4.7,
      "reviews_count": 150,
      "availability": true,
      "url": "https://example.com/product",
      "image_url": "https://example.com/image.jpg",
      "specs": {
        "size": "42",
        "color": "Black"
      },
      "similarity_score": 0.98,
      "store_name": "Sneaker Store",
      "distance_km": 2.5
    }
  ],
  "analysis": {
    "best_value": {
      "product_id": "p1",
      "reasoning": "Best price-to-quality ratio at $99.99"
    },
    "top_3_recommendations": [
      {
        "rank": 1,
        "product_id": "p1",
        "category": "best_value",
        "pros": ["Excellent price", "High rating", "Close location"],
        "cons": ["Limited stock"],
        "reasoning": "Best overall value"
      }
    ],
    "price_analysis": {
      "min_price": 89.99,
      "max_price": 149.99,
      "average_price": 115.00,
      "median_price": 110.00,
      "currency": "USD"
    },
    "summary": "Adidas Samba OG is available at 5 stores with prices ranging from $89.99 to $149.99. The best value is at Sneaker Store for $99.99."
  },
  "cached": false,
  "execution_time_ms": {
    "parse_query": 45,
    "discover_stores": 230,
    "scrape_products": 1250,
    "match_products": 280,
    "analyze": 3500
  },
  "timestamp": "2025-12-10T12:34:56.789Z"
}
```

**Error Responses:**

400 - Invalid location:
```json
{
  "detail": "Location must be within Lebanon boundaries"
}
```

400 - Missing coordinates:
```json
{
  "detail": "Missing latitude or longitude"
}
```

500 - Server error:
```json
{
  "detail": "Internal server error"
}
```

**Status Codes:**
- `200`: Search completed successfully
- `400`: Invalid request (location, coordinates)
- `422`: Validation error (missing fields, wrong types)
- `500`: Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nike shoes size 42",
    "location": {"lat": 33.89, "lng": 35.50}
  }'
```

---

### 3. Search with Streaming Progress

**GET `/api/search/stream`**

Execute search with real-time progress updates. Returns server-sent events (newline-delimited JSON).

**Query Parameters:**
- `query` (string, required): Product search query
- `lat` (float, required): Latitude coordinate
- `lng` (float, required): Longitude coordinate

**Response Format:**
Newline-delimited JSON events (NDJSON)

**Event Types:**

**In-Progress Events:**
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "node": "parse_query",
  "data": {
    "parsed_query": true,
    "execution_time_ms": {"parse_query": 50},
    "errors": []
  }
}
```

**Completion Event:**
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "node": "completed",
  "data": {
    "parsed_query": true,
    "stores_found": 5,
    "products_scraped": 12,
    "products_matched": 10,
    "analysis_complete": true,
    "execution_times": {
      "parse_query": 50,
      "discover_stores": 230,
      "scrape_products": 1250,
      "match_products": 280,
      "analyze": 3500
    },
    "total_errors": 0
  }
}
```

**Node Progress Mapping:**
| Node | Data Field | Meaning |
|------|-----------|---------|
| parse_query | parsed_query | Query successfully parsed |
| discover_stores | stores_found | Number of nearby stores found |
| scrape_products | products_scraped | Products extracted from store websites |
| match_products | products_matched | Products ranked by semantic similarity |
| analyze | analysis_complete | Claude AI analysis generated |

**Status Codes:**
- `200`: Stream opened successfully
- `400`: Invalid location
- `422`: Validation error

**Example with curl:**
```bash
curl "http://localhost:8000/api/search/stream?query=nike+shoes&lat=33.89&lng=35.50"
```

**Example with JavaScript:**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/search/stream?query=nike+shoes&lat=33.89&lng=35.50'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.node}: ${data.status}`);

  if (data.status === 'complete') {
    console.log('Search finished!', data.data);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('Stream error:', error);
  eventSource.close();
};
```

---

### 4. Retrieve Cached Result

**GET `/api/search/{search_id}`**

Retrieve a previously executed search result from cache.

**Path Parameters:**
- `search_id` (string): UUID from initial search response

**Response:**
Same as POST /api/search (SearchResponse)

**Status Codes:**
- `200`: Result found
- `404`: Search not found or expired (1 hour TTL)

**Example:**
```bash
curl http://localhost:8000/api/search/550e8400-e29b-41d4-a716-446655440000
```

---

### 5. Check Search Progress

**GET `/api/search/{search_id}/progress`**

Check if a search result is available in cache without fetching full data.

**Path Parameters:**
- `search_id` (string): UUID from initial search response

**Response:**
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "available": true,
  "timestamp": "2025-12-10T12:34:56.789Z"
}
```

**Status Codes:**
- `200`: Status retrieved

**Example:**
```bash
curl http://localhost:8000/api/search/550e8400-e29b-41d4-a716-446655440000/progress
```

---

## Data Models

### SearchRequest
```json
{
  "query": "string (1-500 chars)",
  "location": {
    "lat": "float (-90 to 90)",
    "lng": "float (-180 to 180)"
  }
}
```

### SearchResponse
```json
{
  "search_id": "string (UUID)",
  "query": "string",
  "location": {
    "lat": "float",
    "lng": "float",
    "address": "string or null"
  },
  "stores_found": "integer",
  "products_found": "integer",
  "results": [
    {
      "product_id": "string",
      "store_id": "string",
      "title": "string",
      "price": "float",
      "currency": "USD|LBP",
      "rating": "float (0-5)",
      "reviews_count": "integer",
      "availability": "boolean",
      "url": "string (URL)",
      "image_url": "string (URL) or null",
      "specs": "object or null",
      "similarity_score": "float (0-1)",
      "store_name": "string",
      "distance_km": "float"
    }
  ],
  "analysis": {
    "best_value": {
      "product_id": "string",
      "reasoning": "string"
    },
    "top_3_recommendations": [
      {
        "rank": "integer (1-3)",
        "product_id": "string",
        "category": "best_value|best_rating|closest|best_overall",
        "pros": ["string"],
        "cons": ["string"],
        "reasoning": "string or null"
      }
    ],
    "price_analysis": {
      "min_price": "float",
      "max_price": "float",
      "average_price": "float",
      "median_price": "float",
      "currency": "USD|LBP"
    },
    "summary": "string"
  },
  "cached": "boolean",
  "execution_time_ms": {
    "parse_query": "integer",
    "discover_stores": "integer",
    "scrape_products": "integer",
    "match_products": "integer",
    "analyze": "integer"
  },
  "timestamp": "ISO 8601 datetime"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Search completed |
| 400 | Bad Request | Invalid location |
| 404 | Not Found | Search ID not in cache |
| 422 | Validation Error | Missing required field |
| 500 | Server Error | Workflow execution failed |

### Error Response Format
```json
{
  "detail": "Human-readable error message"
}
```

### Common Errors

**Invalid Location (400)**
```
Message: "Location must be within Lebanon boundaries"
Latitude: 33.0-34.7
Longitude: 35.1-36.6
```

**Missing Coordinates (400)**
```
Message: "Missing latitude or longitude"
Ensure both lat and lng are provided
```

**Search Not Found (404)**
```
Message: "Search not found or expired"
Reason: Cache cleared after 1 hour
Solution: Run search again
```

**Validation Error (422)**
```
Message: Field validation error details
Examples:
- Empty query string
- Query > 500 characters
- Invalid JSON format
```

---

## Rate Limiting

Currently no rate limiting. Planned for Phase 9+.

---

## Caching Strategy

### In-Memory Cache
- **TTL:** 1 hour
- **Storage:** Application memory
- **Size:** Unlimited (in production, should implement size limits)
- **Use Case:** Fast retrieval of recent searches

### Redis Cache (Future)
- **TTL:** 1 hour for searches, 6 hours for products, 24 hours for stores
- **Shared:** Across multiple server instances
- **Persistence:** Optional

---

## CORS Configuration

Allowed Origins:
- `http://localhost:3000` (dev frontend)
- `http://localhost:5173` (Vite dev)
- `https://wen-arkhas.app` (production)

Allowed Methods: All
Allowed Headers: All

---

## Performance Characteristics

### Typical Response Times

| Endpoint | Min | Avg | Max |
|----------|-----|-----|-----|
| /health | <5ms | <10ms | 50ms |
| /api/search | 4000ms | 6000ms | 10000ms |
| /api/search/stream | 4000ms | 6000ms | 10000ms |
| /api/search/{id} | <10ms | <50ms | 500ms |
| /api/search/{id}/progress | <5ms | <10ms | 50ms |

### Execution Time Breakdown (for /api/search)
```
parse_query:      ~50ms    (NLP parsing)
discover_stores:  ~230ms   (Google Places API)
scrape_products:  ~1250ms  (Web scraping)
match_products:   ~280ms   (Semantic embedding)
analyze:          ~3500ms  (Claude AI API)
─────────────────────────
Total:            ~5310ms  (5.3 seconds average)
```

---

## Examples

### Python Client
```python
import requests
import json

# Search
response = requests.post(
    "http://localhost:8000/api/search",
    json={
        "query": "nike shoes size 42",
        "location": {"lat": 33.89, "lng": 35.50}
    }
)

result = response.json()
print(f"Found {result['products_found']} products")
print(f"Best value: {result['analysis']['best_value']['product_id']}")

# Streaming search
import sseclient

response = requests.get(
    "http://localhost:8000/api/search/stream",
    params={
        "query": "adidas shoes",
        "lat": 33.89,
        "lng": 35.50
    },
    stream=True
)

client = sseclient.SSEClient(response)
for event in client:
    data = json.loads(event.data)
    if data['status'] == 'in_progress':
        print(f"Progress: {data['node']}")
    elif data['status'] == 'complete':
        print("Search complete!")
```

### JavaScript Client
```javascript
// Search
const response = await fetch('http://localhost:8000/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'nike shoes',
    location: { lat: 33.89, lng: 35.50 }
  })
});

const result = await response.json();
console.log(`Found ${result.products_found} products`);
console.log(`Best value: ${result.analysis.best_value.product_id}`);

// Streaming search
const eventSource = new EventSource(
  'http://localhost:8000/api/search/stream?query=nike+shoes&lat=33.89&lng=35.50'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.node}: ${data.status}`);

  if (data.status === 'complete') {
    console.log('Done!');
    eventSource.close();
  }
};
```

### cURL Examples
```bash
# Health check
curl http://localhost:8000/health

# Search (standard)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nike shoes",
    "location": {"lat": 33.89, "lng": 35.50}
  }'

# Streaming search
curl "http://localhost:8000/api/search/stream?query=nike+shoes&lat=33.89&lng=35.50"

# Get cached result
curl http://localhost:8000/api/search/550e8400-e29b-41d4-a716-446655440000

# Check progress
curl http://localhost:8000/api/search/550e8400-e29b-41d4-a716-446655440000/progress
```

---

## OpenAPI Documentation

Auto-generated documentation available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

---

## Roadmap (Future Phases)

- Phase 9: Frontend (Next.js UI with real-time updates)
- Rate limiting and API key authentication
- WebSocket support for bidirectional streaming
- Database persistence (PostgreSQL)
- Advanced analytics and search history
- Multi-language support
