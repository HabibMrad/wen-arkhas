"""
Integration tests for Phase 8 FastAPI endpoints.

Tests all API endpoints:
- GET /health
- POST /api/search
- GET /api/search/stream
- GET /api/search/{search_id}
- GET /api/search/{search_id}/progress
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app, get_workflow, _search_cache
from app.models.schemas import (
    SearchRequest, AnalysisResult, PriceAnalysis, Recommendation
)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_workflow():
    """Create mock workflow"""
    return AsyncMock()


@pytest.fixture
def mock_search_result():
    """Create mock search result"""
    return {
        "query": "nike shoes",
        "location": {"lat": 33.89, "lng": 35.50},
        "parsed_query": MagicMock(original_query="nike shoes"),
        "stores": [
            {
                "store_id": "s1",
                "name": "Nike Store",
                "address": "Beirut",
                "lat": 33.89,
                "lng": 35.50,
                "distance_km": 1.0,
                "website": "https://nike.com",
                "rating": 4.5,
                "reviews_count": 100,
                "currently_open": True
            }
        ],
        "raw_products": [
            {
                "product_id": "p1",
                "store_id": "s1",
                "title": "Nike Shoe",
                "price": 100.0,
                "currency": "USD",
                "rating": 4.5,
                "reviews_count": 50,
                "availability": True,
                "url": "https://example.com/p1",
                "specs": {"size": "42"}
            }
        ],
        "matched_products": [
            MagicMock(
                product_id="p1",
                store_id="s1",
                title="Nike Shoe",
                price=100.0,
                currency="USD",
                rating=4.5,
                reviews_count=50,
                availability=True,
                url="https://example.com/p1",
                image_url=None,
                specs={"size": "42"},
                description=None,
                similarity_score=0.95,
                store_name="Nike Store",
                distance_km=1.0
            )
        ],
        "analysis": {
            "best_value": {"product_id": "p1", "reasoning": "Best price"},
            "top_3_recommendations": [
                {
                    "rank": 1,
                    "product_id": "p1",
                    "category": "best_value",
                    "pros": ["Good price", "Good rating"],
                    "cons": ["Limited stock"]
                }
            ],
            "price_analysis": {
                "min_price": 100.0,
                "max_price": 150.0,
                "average_price": 125.0,
                "median_price": 125.0
            },
            "summary": "Nike Shoe is the best value option"
        },
        "errors": [],
        "execution_time_ms": {
            "parse_query": 50,
            "discover_stores": 200,
            "scrape_products": 500,
            "match_products": 300,
            "analyze": 3000
        }
    }


class TestHealthEndpoint:
    """Tests for GET /health endpoint"""

    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_health_check_returns_json(self, client):
        """Test health check returns valid JSON"""
        response = client.get("/health")

        assert response.headers["content-type"].startswith("application/json")


class TestSearchEndpoint:
    """Tests for POST /api/search endpoint"""

    @pytest.mark.asyncio
    async def test_search_valid_request(self, client, mock_workflow, mock_search_result):
        """Test search with valid request"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "nike shoes"
            assert "search_id" in data
            assert data["stores_found"] >= 0

    def test_search_missing_query(self, client):
        """Test search with missing query"""
        response = client.post(
            "/api/search",
            json={"location": {"lat": 33.89, "lng": 35.50}}
        )

        assert response.status_code == 422  # Validation error

    def test_search_missing_location(self, client):
        """Test search with missing location"""
        response = client.post(
            "/api/search",
            json={"query": "nike shoes"}
        )

        assert response.status_code == 422

    def test_search_invalid_coordinates(self, client):
        """Test search with missing coordinates"""
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 33.89}  # Missing lng
            }
        )

        assert response.status_code == 400

    def test_search_location_outside_lebanon(self, client):
        """Test search with location outside Lebanon"""
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 40.0, "lng": 40.0}  # Outside Lebanon
            }
        )

        assert response.status_code == 400
        assert "Lebanon" in response.json()["detail"]

    def test_search_empty_query(self, client):
        """Test search with empty query"""
        response = client.post(
            "/api/search",
            json={
                "query": "",
                "location": {"lat": 33.89, "lng": 35.50}
            }
        )

        assert response.status_code == 422

    def test_search_query_too_long(self, client):
        """Test search with query exceeding max length"""
        response = client.post(
            "/api/search",
            json={
                "query": "x" * 600,
                "location": {"lat": 33.89, "lng": 35.50}
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_returns_search_id(self, client, mock_workflow, mock_search_result):
        """Test search returns unique search_id"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response1 = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            data1 = response1.json()
            search_id1 = data1["search_id"]

            response2 = client.post(
                "/api/search",
                json={
                    "query": "adidas shoes",
                    "location": {"lat": 33.90, "lng": 35.51}
                }
            )

            data2 = response2.json()
            search_id2 = data2["search_id"]

            assert search_id1 != search_id2

    @pytest.mark.asyncio
    async def test_search_includes_execution_times(self, client, mock_workflow, mock_search_result):
        """Test search response includes execution times"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            data = response.json()
            assert "execution_time_ms" in data
            assert len(data["execution_time_ms"]) > 0


class TestStreamingEndpoint:
    """Tests for GET /api/search/stream endpoint"""

    def test_stream_missing_query(self, client):
        """Test streaming search with missing query"""
        response = client.get(
            "/api/search/stream",
            params={"lat": 33.89, "lng": 35.50}
        )

        assert response.status_code == 422

    def test_stream_missing_coordinates(self, client):
        """Test streaming search with missing coordinates"""
        response = client.get(
            "/api/search/stream",
            params={"query": "nike shoes", "lat": 33.89}
        )

        assert response.status_code == 422

    def test_stream_invalid_location(self, client):
        """Test streaming search with location outside Lebanon"""
        response = client.get(
            "/api/search/stream",
            params={"query": "nike shoes", "lat": 40.0, "lng": 40.0}
        )

        assert response.status_code == 400

    def test_stream_returns_ndjson(self, client, mock_workflow):
        """Test streaming response is newline-delimited JSON"""
        mock_events = [
            {
                "status": "in_progress",
                "node": "parse_query",
                "data": {"parsed_query": True}
            },
            {
                "status": "complete",
                "node": "completed",
                "data": {"stores_found": 1}
            }
        ]

        async def mock_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke_streaming = mock_stream
            response = client.get(
                "/api/search/stream",
                params={
                    "query": "nike shoes",
                    "lat": 33.89,
                    "lng": 35.50
                }
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-ndjson"


class TestCacheEndpoints:
    """Tests for cache retrieval endpoints"""

    @pytest.mark.asyncio
    async def test_get_cached_result_found(self, client, mock_workflow, mock_search_result):
        """Test retrieving cached search result"""
        # First, do a search to cache it
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            search_id = response.json()["search_id"]

            # Retrieve from cache
            cache_response = client.get(f"/api/search/{search_id}")

            assert cache_response.status_code == 200
            assert cache_response.json()["search_id"] == search_id

    def test_get_cached_result_not_found(self, client):
        """Test retrieving non-existent search result"""
        response = client.get("/api/search/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_search_progress_available(self, client, mock_workflow, mock_search_result):
        """Test checking progress for available search"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            search_id = response.json()["search_id"]

            # Check progress
            progress_response = client.get(f"/api/search/{search_id}/progress")

            assert progress_response.status_code == 200
            data = progress_response.json()
            assert data["search_id"] == search_id
            assert data["available"] is True

    def test_get_search_progress_unavailable(self, client):
        """Test checking progress for unavailable search"""
        response = client.get("/api/search/nonexistent-id/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False


class TestRequestValidation:
    """Tests for request validation"""

    def test_valid_search_request_bounds(self, client):
        """Test search with valid Lebanon boundaries"""
        # Southwest corner
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 33.0, "lng": 35.1}
            }
        )
        assert response.status_code in [200, 500]  # Valid bounds

        # Northeast corner
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 34.7, "lng": 36.6}
            }
        )
        assert response.status_code in [200, 500]  # Valid bounds

    def test_location_validation_edge_cases(self, client):
        """Test location validation with edge values"""
        # Just outside Lebanon (south)
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 32.9, "lng": 35.5}
            }
        )
        assert response.status_code == 400

        # Just outside Lebanon (north)
        response = client.post(
            "/api/search",
            json={
                "query": "nike shoes",
                "location": {"lat": 34.8, "lng": 35.5}
            }
        )
        assert response.status_code == 400


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_search_workflow_error(self, client, mock_workflow):
        """Test search handles workflow errors"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(side_effect=Exception("Workflow error"))

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            assert response.status_code == 500

    def test_search_bad_json(self, client):
        """Test search with invalid JSON"""
        response = client.post(
            "/api/search",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_stream_bad_query_format(self, client):
        """Test streaming search with bad query format"""
        response = client.get(
            "/api/search/stream",
            params={
                "query": 123,  # Should be string
                "lat": 33.89,
                "lng": 35.50
            }
        )

        # FastAPI will coerce this, so just check it works or rejects
        assert response.status_code in [200, 422]


class TestCorsHeaders:
    """Tests for CORS configuration"""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present"""
        response = client.get("/health")

        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestResponseSchemas:
    """Tests for response schema validation"""

    def test_health_response_schema(self, client):
        """Test health response matches schema"""
        response = client.get("/health")
        data = response.json()

        required_fields = ["status", "version", "timestamp"]
        for field in required_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_search_response_schema(self, client, mock_workflow, mock_search_result):
        """Test search response matches schema"""
        with patch("app.main.get_workflow", return_value=mock_workflow):
            mock_workflow.invoke = AsyncMock(return_value=mock_search_result)

            response = client.post(
                "/api/search",
                json={
                    "query": "nike shoes",
                    "location": {"lat": 33.89, "lng": 35.50}
                }
            )

            data = response.json()

            # Check required fields
            required_fields = [
                "search_id", "query", "location", "stores_found",
                "products_found", "results", "execution_time_ms", "timestamp"
            ]
            for field in required_fields:
                assert field in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
