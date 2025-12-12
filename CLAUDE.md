# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Wen-Arkhas** (Arabic: "Where is the cheapest?") is an AI-powered local price comparison platform that finds the cheapest products near a user's location. It combines multi-agent AI orchestration, semantic search, and web scraping to deliver real-time product recommendations for the Lebanese market.

## Architecture

The system uses a multi-agent LangGraph workflow with 5 sequential agents:

1. **QueryParserAgent** - Extracts structured product attributes (brand, model, size, gender, color) from user queries
2. **StoreDiscoveryAgent** - Discovers nearby stores using Google Places API and location services
3. **ScraperAgent** - Extracts product listings from store websites using Playwright and BeautifulSoup
4. **RAGAgent** - Performs semantic matching using Pinecone vector embeddings to rank products
5. **AnalysisAgent** - Generates intelligent recommendations using Claude AI via OpenRouter API

### Key Design Patterns

- **LangGraph Workflow** - Sequential agent orchestration with error accumulation (agents don't fail the workflow)
- **Multi-tier Caching** - Redis with different TTLs: stores (24h), products (6h), searches (1h)
- **Semantic Search** - Sentence-transformers for embeddings + Pinecone for vector storage
- **Graceful Degradation** - Agents provide best-effort results; workflow continues even if individual steps fail
- **Rate Limiting** - 1 request/second per domain to respect server resources

## Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- LangGraph for workflow orchestration
- OpenRouter API (Claude Sonnet 4)
- Pinecone (vector database)
- Redis (caching)
- Playwright + BeautifulSoup4 (web scraping)
- Google Places API (store discovery)
- Sentence-transformers (embeddings)

**Frontend:**
- Next.js 14+ with TypeScript
- Tailwind CSS + shadcn/ui components
- Leaflet (maps)
- Zustand (state management)

## Directory Structure

```
wen-arkhas/
├── backend/
│   ├── app/
│   │   ├── agents/              # 5 agent implementations (query_parser, store_discovery, scraper, rag, analysis)
│   │   ├── services/            # Core business logic (location, cache, embedding, pinecone, openrouter, query_parser)
│   │   ├── graph/               # LangGraph workflow (workflow.py, state.py)
│   │   ├── scrapers/            # Playwright-based web scraping
│   │   ├── models/              # Pydantic schemas
│   │   ├── main.py              # FastAPI app + 5 REST endpoints
│   │   ├── config.py            # Settings & environment configuration
│   │   └── logging_config.py    # Logging setup
│   ├── tests/                   # 190+ test cases (phase-organized)
│   ├── requirements.txt         # Dependencies
│   ├── .env.example             # Environment template
│   └── conftest.py              # Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (layout, home, results)
│   │   ├── components/          # React components (SearchInput, ProductCard)
│   │   ├── lib/                 # Utilities (API client)
│   │   ├── hooks/               # Custom hooks (useSearch)
│   │   └── store/               # Zustand state (searchStore)
│   ├── package.json
│   └── .env.example
└── docker-compose.yml           # Development environment setup
```

## Common Commands

### Backend Development

```bash
# Setup
cd wen-arkhas/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with API keys (OpenRouter, Google Places, Pinecone, Redis)

# Start Redis (required)
redis-server  # Or: docker run -p 6379:6379 redis

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health

# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_services.py -v                    # Phase 2 (core services)
pytest tests/test_agents_phase3.py -v              # Phase 3 (agents)
pytest tests/test_scrapers_phase4.py -v            # Phase 4 (scraping)
pytest tests/test_embedding_phase5.py -v           # Phase 5 (embeddings)
pytest tests/test_analysis_phase6.py -v            # Phase 6 (analysis)
pytest tests/test_workflow_phase7.py -v            # Phase 7 (workflow)
pytest tests/test_api_phase8.py -v                 # Phase 8 (API)

# Run single test
pytest tests/test_api_phase8.py::test_search_endpoint -v

# Coverage report
pytest --cov=app --cov-report=html
```

### Frontend Development

```bash
# Setup
cd wen-arkhas/frontend
npm install

# Development server (runs on http://localhost:3000)
npm run dev

# Build for production
npm build

# Linting
npm run lint

# Testing
npm test
npm test -- --watch
```

### Docker & Deployment

```bash
# Local development with all services
docker-compose up

# Backend only
cd wen-arkhas/backend
docker build -t wen-arkhas-backend .
docker run -p 8000:8000 --env-file .env wen-arkhas-backend

# Frontend only
cd wen-arkhas/frontend
docker build -t wen-arkhas-frontend .
docker run -p 3000:3000 wen-arkhas-frontend
```

## Key Services & Utilities

### LocationService (`app/services/location.py`)
- `validate_location(lat, lng)` - Validates user is in Lebanon bounds
- `calculate_distance(loc1, loc2)` - Haversine distance between coordinates
- `get_search_radius(location, radius_km)` - Returns bounding box for API searches
- `sort_by_distance(stores, location)` - Sorts stores by proximity

### CacheManager (`app/services/cache.py`)
- `get_stores(key)` / `set_stores(key, stores)` - Cache store listings (24h TTL)
- `get_products(key)` / `set_products(key, products)` - Cache products (6h TTL)
- `get_search(key)` / `set_search(key, result)` - Cache search results (1h TTL)
- Uses Redis; gracefully disables if Redis unavailable

### QueryParser (`app/services/query_parser.py`)
- `parse(query)` - Extracts brand, model, size, gender, color from query
- `build_search_terms(parsed)` - Builds optimized search string
- `get_fallback_category(query)` - Detects product category

### EmbeddingService (`app/services/embedding.py`)
- `embed_text(text)` - Generates vector embeddings using sentence-transformers
- Used for semantic search in RAGAgent

### PineconeDB (`app/services/pinecone_db.py`)
- `upsert_products(products)` - Stores product vectors
- `query_similar(query_embedding, top_k)` - Retrieves similar products

### OpenRouterService (`app/services/openrouter.py`)
- `analyze_products(products_context)` - Gets Claude Sonnet 4 recommendations
- Handles cost tracking and rate limiting

## API Endpoints

All endpoints are under `/api/` prefix (docs at `/api/docs`).

### POST /api/search
Main search endpoint. Executes full workflow.

**Request:**
```json
{
  "query": "adidas Samba man 42",
  "location": {"lat": 33.89, "lng": 35.50}
}
```

**Response:**
```json
{
  "search_id": "uuid",
  "query": "...",
  "location": {...},
  "parsed_query": {...},
  "stores": [...],
  "raw_products": [...],
  "matched_products": [...],
  "analysis": {...},
  "execution_time_ms": {...},
  "errors": []
}
```

### GET /api/search/stream?query=...&lat=...&lng=...
Streaming endpoint for real-time progress updates (Server-Sent Events).

### GET /api/search/{search_id}
Retrieve cached result.

### GET /api/search/{search_id}/progress
Check search progress during execution.

### GET /health
Health check endpoint.

## State Management (LangGraph)

The `SearchState` object flows through all 5 agents. Key fields:

```python
{
  "query": str,
  "location": {"lat": float, "lng": float},
  "parsed_query": {"brand": str, "model": str, "size": str, "gender": str, "color": str},
  "stores": [{"id": str, "name": str, "address": str, "lat": float, "lng": float, ...}],
  "raw_products": [{"title": str, "price": float, "url": str, ...}],
  "matched_products": [{"title": str, "price": float, "similarity_score": float, ...}],
  "analysis": {"recommendations": [...], "summary": str},
  "errors": [str],
  "execution_time_ms": {"parse_query": int, "discover_stores": int, ...}
}
```

## Error Handling & Resilience

- **No workflow failure on agent errors** - Each agent catches exceptions and appends to `state["errors"]`
- **Retry logic** - Store discovery retries if < 3 stores found (max 2 retries)
- **Fallbacks** - Each agent provides graceful degradation
- **Error accumulation** - All errors logged but workflow completes

## Important Configuration

### Environment Variables (backend/.env)

```
OPENROUTER_API_KEY=         # Claude Sonnet 4 access
GOOGLE_PLACES_API_KEY=      # Store discovery
PINECONE_API_KEY=           # Vector database
PINECONE_INDEX_NAME=        # Usually "wen-arkhas"
PINECONE_HOST=              # From Pinecone console
REDIS_URL=                  # redis://localhost:6379
ENVIRONMENT=                # "development" or "production"
DEBUG=                       # true or false
```

### Frontend Environment (frontend/.env.local)

```
NEXT_PUBLIC_API_URL=        # Backend URL (e.g., http://localhost:8000)
```

## Testing Strategy

- **Unit tests** - Individual functions and services (Phase 2-6)
- **Integration tests** - Agent workflows (Phase 7)
- **API tests** - REST endpoints (Phase 8)
- **Coverage target** - 80%+ code coverage
- All tests use pytest with async support (`pytest-asyncio`)

## Performance & Optimization

- **Caching** - Aggressive Redis caching reduces API calls and improves response time
- **Rate limiting** - 1 req/sec per domain prevents blocking
- **Streaming API** - Real-time progress updates via SSE instead of polling
- **Vector search** - Pinecone provides O(1) semantic matching vs O(n) comparison
- **Lazy loading** - Products only scraped from stores with potential matches

## Security & Privacy

- **Location privacy** - User locations not stored permanently
- **robots.txt compliance** - Respect website scraping guidelines
- **API key management** - Store in .env, never commit secrets
- **CORS configured** - Localhost + production domains only
- **Rate limiting** - Prevents abuse and respects target sites

## Deployment Notes

- **Backend** - Deployable to Railway with Docker
- **Frontend** - Deployable to Vercel
- **Health checks** - Both services have `/health` endpoints for monitoring
- **Environment parity** - .env.example documents all required variables
- **Database** - Requires Redis + Pinecone (free tier: 1M vectors)
