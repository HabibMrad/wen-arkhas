"""
PHASE 8: FastAPI endpoints for Wen-Arkhas price comparison platform.

Endpoints:
- GET /health - Health check
- POST /api/search - Main search endpoint (standard)
- GET /api/search/stream - Streaming search with real-time progress
- GET /api/search/{search_id} - Retrieve cached result
- GET /api/search/{search_id}/progress - Check search progress
"""

import logging
import uuid
import asyncio
import json
from typing import Dict, AsyncGenerator, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graph.workflow import WorkflowExecutor
from app.services.cache import CacheManager
from app.services.location import LocationService
from app.models.schemas import SearchResponse, MatchedProduct, LocationModel
from app.config import settings

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Wen-Arkhas API",
    description="AI-powered local price comparison platform for Lebanon",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://wen-arkhas.app",
        "https://wen-arkhas.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class SearchRequest(BaseModel):
    """Search request with query and location"""
    query: str = Field(..., min_length=1, max_length=500, description="Product search query")
    location: Dict[str, float] = Field(..., description="GPS coordinates - {'lat': float, 'lng': float}")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "adidas Samba man 42",
                "location": {"lat": 33.89, "lng": 35.50}
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SearchProgressResponse(BaseModel):
    """Real-time search progress"""
    search_id: str
    node: str
    status: str  # "in_progress" or "complete"
    data: Dict


class SearchErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
    search_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Global workflow instance
_workflow = None
_search_cache = {}  # search_id -> (result, timestamp)


def get_workflow() -> WorkflowExecutor:
    """Get or create global workflow executor"""
    global _workflow
    if _workflow is None:
        logger.info("Creating global workflow executor")
        _workflow = WorkflowExecutor(use_complete=True)
    return _workflow


async def cleanup_old_cache():
    """Remove cache entries older than 1 hour"""
    now = datetime.utcnow()
    expired = [
        sid for sid, (_, ts) in _search_cache.items()
        if now - ts > timedelta(hours=1)
    ]
    for sid in expired:
        del _search_cache[sid]
        logger.debug(f"Removed expired cache entry: {sid}")


async def format_search_response(
    search_id: str,
    query: str,
    location: Dict[str, float],
    workflow_result: Dict
) -> SearchResponse:
    """Format workflow result into SearchResponse"""
    from app.models.schemas import (
        LocationModel, AnalysisResult, PriceAnalysis
    )

    try:
        # Extract analysis if available
        analysis = None
        if workflow_result.get("analysis"):
            analysis_data = workflow_result["analysis"]
            # Build recommendations from analysis
            recommendations = []
            if "top_3_recommendations" in analysis_data:
                for rec in analysis_data["top_3_recommendations"]:
                    from app.models.schemas import Recommendation
                    recommendations.append(
                        Recommendation(
                            rank=rec.get("rank", 0),
                            product_id=rec.get("product_id", ""),
                            category=rec.get("category", "best_value"),
                            pros=rec.get("pros", []),
                            cons=rec.get("cons", []),
                            reasoning=rec.get("reasoning", "")
                        )
                    )

            # Build price analysis
            price_analysis = None
            if "price_analysis" in analysis_data:
                pa = analysis_data["price_analysis"]
                price_analysis = PriceAnalysis(
                    min_price=pa.get("min_price", 0),
                    max_price=pa.get("max_price", 0),
                    average_price=pa.get("average_price", 0),
                    median_price=pa.get("median_price", 0)
                )

            analysis = AnalysisResult(
                best_value=analysis_data.get("best_value"),
                top_3_recommendations=recommendations,
                price_analysis=price_analysis,
                summary=analysis_data.get("summary", "")
            )

        # Extract matched products
        matched = []
        if workflow_result.get("matched_products"):
            for product in workflow_result["matched_products"]:
                if isinstance(product, MatchedProduct):
                    matched.append(product)

        # Build response
        response = SearchResponse(
            search_id=search_id,
            query=query,
            location=LocationModel(lat=location["lat"], lng=location["lng"]),
            stores_found=len(workflow_result.get("stores", [])),
            products_found=len(workflow_result.get("raw_products", [])),
            results=matched,
            analysis=analysis,
            cached=False,
            execution_time_ms=workflow_result.get("execution_time_ms", {}),
            timestamp=datetime.utcnow()
        )

        return response

    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}", exc_info=True)
        raise


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring service status"""
    logger.debug("Health check requested")
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0"
    )


@app.post("/api/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    Main search endpoint for product price comparison.

    Process:
    1. Validate location (must be in Lebanon)
    2. Check cache
    3. Run LangGraph workflow if not cached
    4. Return results with analysis

    Args:
        request: SearchRequest with query and location

    Returns:
        SearchResponse with products, analysis, and execution metrics

    Raises:
        HTTPException: 400 for invalid location, 500 for server errors
    """
    search_id = str(uuid.uuid4())
    logger.info(f"Search initiated: {search_id} - Query: {request.query}")

    try:
        # Validate location
        lat, lng = request.location.get("lat"), request.location.get("lng")
        if not lat or not lng:
            logger.warning(f"Search {search_id}: Missing coordinates")
            raise HTTPException(status_code=400, detail="Missing latitude or longitude")

        if not LocationService.validate_location(lat, lng):
            logger.warning(f"Search {search_id}: Location outside Lebanon bounds")
            raise HTTPException(
                status_code=400,
                detail="Location must be within Lebanon boundaries"
            )

        # Check in-memory cache
        if search_id in _search_cache:
            result, _ = _search_cache[search_id]
            logger.info(f"Search {search_id}: Returned from in-memory cache")
            result.cached = True
            return result

        # Check Redis cache (search cache, 1 hour TTL)
        cache_key = CacheManager.generate_key("searches", search_id, "")
        cached_result = None
        try:
            # Placeholder for Redis cache lookup
            pass
        except Exception as e:
            logger.debug(f"Cache lookup failed: {str(e)}")

        # Execute workflow
        logger.info(f"Search {search_id}: Starting workflow execution")
        workflow = get_workflow()
        workflow_result = await workflow.invoke(request.query, request.location)

        # Format response
        response = await format_search_response(
            search_id,
            request.query,
            request.location,
            workflow_result
        )

        # Store in cache
        _search_cache[search_id] = (response, datetime.utcnow())

        logger.info(
            f"Search {search_id}: Completed - "
            f"{response.stores_found} stores, "
            f"{response.products_found} products, "
            f"Time: {sum(response.execution_time_ms.values()) if response.execution_time_ms else 0}ms"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search {search_id} error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def search_stream_generator(
    query: str,
    location: Dict[str, float]
) -> AsyncGenerator[str, None]:
    """Generator for streaming search results"""
    search_id = str(uuid.uuid4())
    logger.info(f"Streaming search initiated: {search_id} - Query: {query}")

    try:
        # Validate location
        lat, lng = location.get("lat"), location.get("lng")
        if not lat or not lng or not LocationService.validate_location(lat, lng):
            yield json.dumps({
                "status": "error",
                "search_id": search_id,
                "message": "Invalid location"
            }) + "\n"
            return

        # Get workflow
        workflow = get_workflow()

        # Execute workflow to get final result
        workflow_result = await workflow.invoke(query, location)

        # Stream events and capture the final result
        async for event in workflow.invoke_streaming(query, location):
            payload = {
                "search_id": search_id,
                **event
            }
            yield json.dumps(payload) + "\n"
            await asyncio.sleep(0.1)  # Brief delay between events

        # Format and cache the final result
        logger.info(f"Streaming search {search_id}: Formatting and caching result")
        response = await format_search_response(
            search_id,
            query,
            location,
            workflow_result
        )
        _search_cache[search_id] = (response, datetime.utcnow())

        logger.info(f"Streaming search {search_id}: Completed and cached")

    except Exception as e:
        logger.error(f"Streaming search {search_id} error: {str(e)}")
        yield json.dumps({
            "status": "error",
            "search_id": search_id,
            "message": str(e)
        }) + "\n"


@app.get("/api/search/stream")
async def search_stream(
    query: str = Query(..., min_length=1, max_length=500),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180)
):
    """
    Streaming search endpoint for real-time progress updates.

    Stream format: Server-sent events with JSON payloads
    Each event contains progress from individual agents

    Args:
        query: Product search query
        lat: Latitude coordinate
        lng: Longitude coordinate

    Returns:
        StreamingResponse with JSON events (newline-delimited)

    Example:
        curl "http://localhost:8000/api/search/stream?query=nike+shoes&lat=33.89&lng=35.50"
    """
    logger.info(f"Stream search requested: {query} at {lat},{lng}")

    # Validate location
    if not LocationService.validate_location(lat, lng):
        return StreamingResponse(
            json.dumps({
                "status": "error",
                "message": "Location must be within Lebanon boundaries"
            }),
            status_code=400,
            media_type="application/json"
        )

    return StreamingResponse(
        search_stream_generator(query, {"lat": lat, "lng": lng}),
        media_type="application/x-ndjson"
    )


@app.get("/api/search/{search_id}")
async def get_search_result(search_id: str):
    """
    Retrieve cached search result by ID.

    Args:
        search_id: Search ID from initial search

    Returns:
        SearchResponse if found

    Raises:
        HTTPException: 404 if search not found
    """
    logger.debug(f"Retrieving search result: {search_id}")

    # Check in-memory cache
    if search_id in _search_cache:
        result, _ = _search_cache[search_id]
        logger.debug(f"Search {search_id}: Found in cache")
        return result

    # Could check Redis cache here
    logger.warning(f"Search {search_id}: Not found")
    raise HTTPException(status_code=404, detail="Search not found or expired")


@app.get("/api/search/{search_id}/progress")
async def get_search_progress(search_id: str):
    """
    Check if search result is available.

    Args:
        search_id: Search ID

    Returns:
        Status with available flag
    """
    logger.debug(f"Checking progress for search: {search_id}")

    available = search_id in _search_cache
    return {
        "search_id": search_id,
        "available": available,
        "timestamp": datetime.utcnow()
    }


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Wen-Arkhas API starting up")
    logger.info("Initializing workflow executor")
    get_workflow()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Wen-Arkhas API shutting down")
    # Could cleanup resources here if needed


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
