"""
Unit tests for Phase 6 LLM analysis and recommendations.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.agents.analysis import AnalysisAgent
from app.services.openrouter import OpenRouterClient
from app.models.schemas import MatchedProduct, ParsedQuery


class TestOpenRouterClient:
    """Tests for OpenRouterClient"""

    def test_init(self):
        """Test OpenRouterClient initialization"""
        client = OpenRouterClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.base_url == "https://openrouter.ai/api/v1"

    def test_build_analysis_prompt(self):
        """Test building analysis prompt"""
        client = OpenRouterClient()

        products = [
            {
                "id": "p1",
                "title": "Product 1",
                "price": 99.99,
                "currency": "USD",
                "rating": 4.5,
                "reviews": 50,
                "store": "Store 1",
                "distance_km": 2.0,
                "available": True,
                "url": "https://example.com/p1",
                "similarity": 95.0
            }
        ]

        prompt = client._build_analysis_prompt(
            products,
            "test query",
            None
        )

        assert "Product 1" in prompt
        assert "99.99" in prompt
        assert "test query" in prompt
        assert "JSON" in prompt

    @pytest.mark.asyncio
    async def test_call_claude_valid(self):
        """Test calling Claude API"""
        client = OpenRouterClient()

        # Mock response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "best_value": {"product_id": "p1", "reasoning": "Best price"},
                            "top_3_recommendations": [],
                            "price_analysis": {
                                "min_price": 100,
                                "max_price": 200,
                                "average_price": 150,
                                "median_price": 150
                            },
                            "summary": "Test summary"
                        })
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )

            result = await client._call_claude("test prompt")

            assert result is not None
            assert "best_value" in result
            assert result["best_value"]["product_id"] == "p1"

    @pytest.mark.asyncio
    async def test_call_claude_invalid_json(self):
        """Test handling invalid JSON response"""
        client = OpenRouterClient()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Not valid JSON"
                    }
                }
            ],
            "usage": {}
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )

            result = await client._call_claude("test prompt")

            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_products_valid(self):
        """Test analyzing products"""
        client = OpenRouterClient()

        products = [
            {
                "id": "p1",
                "title": "Product 1",
                "price": 99.99,
                "currency": "USD",
                "rating": 4.5,
                "reviews": 50,
                "store": "Store 1",
                "distance_km": 2.0,
                "available": True,
                "url": "https://example.com",
                "similarity": 95.0
            }
        ]

        mock_analysis = {
            "best_value": {"product_id": "p1", "reasoning": "Best value"},
            "top_3_recommendations": [],
            "price_analysis": {
                "min_price": 99.99,
                "max_price": 99.99,
                "average_price": 99.99,
                "median_price": 99.99
            },
            "summary": "Test summary"
        }

        with patch.object(client, "_call_claude", return_value=mock_analysis):
            result = await client.analyze_products(products, "test query")

            assert result is not None
            assert result["best_value"]["product_id"] == "p1"

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing client"""
        client = OpenRouterClient()

        # Mock the client
        client.client = AsyncMock()

        await client.close()

        assert client.client.aclose.called


class TestAnalysisAgent:
    """Tests for AnalysisAgent"""

    def test_init(self):
        """Test AnalysisAgent initialization"""
        with patch("app.services.openrouter.OpenRouterClient"):
            agent = AnalysisAgent()

            assert agent.client is not None

    def test_prepare_products_for_analysis(self):
        """Test preparing products for analysis"""
        with patch("app.services.openrouter.OpenRouterClient"):
            agent = AnalysisAgent()

            products = [
                MatchedProduct(
                    product_id="p1",
                    store_id="s1",
                    title="Product 1",
                    price=99.99,
                    currency="USD",
                    rating=4.5,
                    reviews_count=50,
                    availability=True,
                    url="https://example.com",
                    similarity_score=0.95,
                    store_name="Store 1",
                    distance_km=2.0
                )
            ]

            prepared = agent._prepare_products_for_analysis(products)

            assert len(prepared) == 1
            assert prepared[0]["title"] == "Product 1"
            assert prepared[0]["price"] == 99.99
            assert prepared[0]["similarity"] == 95.0  # Converted to percentage

    @pytest.mark.asyncio
    async def test_execute_no_products(self):
        """Test execute with no products"""
        with patch("app.services.openrouter.OpenRouterClient"):
            agent = AnalysisAgent()

            state = {
                "matched_products": [],
                "parsed_query": ParsedQuery(
                    brand="Nike",
                    original_query="nike",
                    model=None,
                    category=None,
                    size=None,
                    gender=None,
                    color=None
                ),
                "analysis": None,
                "errors": [],
                "execution_time_ms": {}
            }

            result = await agent.execute(state)

            assert result["analysis"] is None

    @pytest.mark.asyncio
    async def test_execute_with_products(self):
        """Test execute with matched products"""
        with patch("app.services.openrouter.OpenRouterClient"):
            agent = AnalysisAgent()

            product = MatchedProduct(
                product_id="p1",
                store_id="s1",
                title="Product 1",
                price=99.99,
                currency="USD",
                rating=4.5,
                reviews_count=50,
                availability=True,
                url="https://example.com",
                similarity_score=0.95,
                store_name="Store 1",
                distance_km=2.0
            )

            analysis_result = {
                "best_value": {"product_id": "p1", "reasoning": "Best value"},
                "top_3_recommendations": [],
                "price_analysis": {
                    "min_price": 99.99,
                    "max_price": 99.99,
                    "average_price": 99.99,
                    "median_price": 99.99
                },
                "summary": "Test summary"
            }

            agent.client = AsyncMock()
            agent.client.analyze_products = AsyncMock(return_value=analysis_result)

            state = {
                "matched_products": [product],
                "parsed_query": ParsedQuery(
                    brand="Nike",
                    original_query="nike",
                    model=None,
                    category=None,
                    size=None,
                    gender=None,
                    color=None
                ),
                "analysis": None,
                "errors": [],
                "execution_time_ms": {}
            }

            result = await agent.execute(state)

            assert result["analysis"] is not None
            assert "execution_time_ms" in result


class TestAnalysisIntegration:
    """Integration tests for analysis system"""

    def test_price_analysis_calculation(self):
        """Test price analysis data"""
        prices = [99.99, 149.99, 199.99]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        assert min_price == 99.99
        assert max_price == 199.99
        assert 149 < avg_price < 150

    def test_recommendation_structure(self):
        """Test recommendation structure"""
        recommendation = {
            "rank": 1,
            "product_id": "p1",
            "category": "best_value",
            "pros": ["Good price", "Good rating"],
            "cons": ["Far away"]
        }

        assert recommendation["rank"] == 1
        assert len(recommendation["pros"]) == 2
        assert len(recommendation["cons"]) == 1

    def test_matched_product_to_analysis_format(self):
        """Test converting MatchedProduct to analysis format"""
        product = MatchedProduct(
            product_id="p1",
            store_id="s1",
            title="Adidas Samba",
            price=99.99,
            currency="USD",
            rating=4.5,
            reviews_count=50,
            availability=True,
            url="https://example.com/p1",
            similarity_score=0.95,
            store_name="Nike Store",
            distance_km=2.5,
            specs={"color": "black", "size": "42"}
        )

        analysis_format = {
            "id": product.product_id,
            "title": product.title,
            "price": product.price,
            "rating": product.rating,
            "similarity": round(product.similarity_score * 100, 1),
            "distance_km": product.distance_km
        }

        assert analysis_format["id"] == "p1"
        assert analysis_format["similarity"] == 95.0
        assert analysis_format["distance_km"] == 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
