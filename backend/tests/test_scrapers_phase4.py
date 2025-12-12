"""
Unit tests for Phase 4 scrapers and scraper agent.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.generic import GenericScraper, create_generic_scraper
from app.agents.scraper import ScraperAgent
from app.models.schemas import ProductModel, ParsedQuery


class TestBaseScraper:
    """Tests for BaseScraper base class"""

    def test_init(self):
        """Test BaseScraper initialization"""
        # BaseScraper is abstract, so we test with GenericScraper
        scraper = GenericScraper("Test Store", "https://test.com")

        assert scraper.store_name == "Test Store"
        assert scraper.store_url == "https://test.com"
        assert scraper.rate_limit_delay == 1.0

    def test_validate_product_valid(self):
        """Test validating a valid product"""
        scraper = GenericScraper("Test Store", "https://test.com")

        product = ProductModel(
            product_id="123",
            store_id="test",
            title="Test Product",
            price=99.99,
            url="https://test.com/product/123"
        )

        assert scraper._validate_product(product) is True

    def test_validate_product_invalid_price(self):
        """Test validating product with invalid price"""
        scraper = GenericScraper("Test Store", "https://test.com")

        product = ProductModel(
            product_id="123",
            store_id="test",
            title="Test Product",
            price=-10.0,  # Negative price
            url="https://test.com/product/123"
        )

        assert scraper._validate_product(product) is False

    def test_build_product(self):
        """Test building a product"""
        scraper = GenericScraper("Test Store", "https://test.com")

        product = scraper._build_product(
            product_id="123",
            store_id="test",
            title="Test Product",
            price=99.99,
            rating=4.5,
            reviews_count=50
        )

        assert product.product_id == "123"
        assert product.title == "Test Product"
        assert product.price == 99.99
        assert product.rating == 4.5

    def test_get_store_id(self):
        """Test getting store ID from URL"""
        scraper = GenericScraper("Nike", "https://www.nike.com")
        store_id = scraper.get_store_id()

        assert "nike" in store_id.lower()


class TestGenericScraper:
    """Tests for GenericScraper"""

    def test_init(self):
        """Test GenericScraper initialization"""
        scraper = GenericScraper("Test Store", "https://test.com")

        assert scraper.store_name == "Test Store"
        assert scraper.store_url == "https://test.com"
        assert scraper.client is None

    def test_build_search_url(self):
        """Test building search URL"""
        scraper = GenericScraper("Test Store", "https://test.com")

        url = scraper._build_search_url("adidas shoes")
        assert "search" in url.lower()
        assert "adidas" in url.lower()

    def test_parse_price_valid(self):
        """Test parsing valid prices"""
        scraper = GenericScraper("Test", "https://test.com")

        assert scraper._parse_price("$99.99") == 99.99
        assert scraper._parse_price("USD 50.00") == 50.0
        assert scraper._parse_price("100") == 100.0

    def test_parse_price_invalid(self):
        """Test parsing invalid prices"""
        scraper = GenericScraper("Test", "https://test.com")

        assert scraper._parse_price("no price") is None
        assert scraper._parse_price("") is None

    @patch("httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_get_client(self, mock_client_class):
        """Test getting HTTP client"""
        scraper = GenericScraper("Test", "https://test.com")

        client = await scraper._get_client()
        assert client is not None
        assert scraper.client is not None

    def test_create_generic_scraper(self):
        """Test scraper factory function"""
        scraper = create_generic_scraper("Test", "https://test.com")

        assert isinstance(scraper, GenericScraper)
        assert scraper.store_name == "Test"


class TestScraperAgent:
    """Tests for ScraperAgent"""

    def test_init(self):
        """Test ScraperAgent initialization"""
        agent = ScraperAgent()

        assert agent.cache is not None
        assert agent.active_scrapers == {}

    def test_get_scraper_type_playwright(self):
        """Test scraper type detection for Playwright sites"""
        agent = ScraperAgent()

        assert agent._get_scraper_type("https://nike.com") == "playwright"
        assert agent._get_scraper_type("https://amazon.com") == "playwright"

    def test_get_scraper_type_generic(self):
        """Test scraper type detection for generic sites"""
        agent = ScraperAgent()

        # Unknown sites default to generic
        scraper_type = agent._get_scraper_type("https://unknown-store.com")
        assert scraper_type == "generic"

    def test_build_search_terms(self):
        """Test building search terms from parsed query"""
        agent = ScraperAgent()

        parsed = ParsedQuery(
            brand="Adidas",
            model="Samba",
            category="shoes",
            size="42",
            gender="men",
            color="black",
            original_query="adidas samba"
        )

        terms = agent._build_search_terms(parsed)

        assert "Adidas" in terms
        assert "Samba" in terms
        assert "42" in terms or "Samba" in terms  # Should have multiple terms

    def test_build_search_terms_fallback(self):
        """Test fallback to original query"""
        agent = ScraperAgent()

        parsed = ParsedQuery(
            brand=None,
            model=None,
            category=None,
            size=None,
            gender=None,
            color=None,
            original_query="custom search"
        )

        terms = agent._build_search_terms(parsed)
        assert terms == "custom search"

    def test_get_cache_key(self):
        """Test cache key generation"""
        agent = ScraperAgent()

        key = agent._get_cache_key("store_123", "adidas shoes")

        assert "products" in key
        assert "store_123" in key

    @pytest.mark.asyncio
    async def test_execute_no_stores(self):
        """Test execute with no stores"""
        agent = ScraperAgent()

        state = {
            "stores": [],
            "parsed_query": ParsedQuery(
                brand="Nike",
                original_query="nike shoes",
                model=None,
                category="shoes",
                size=None,
                gender=None,
                color=None
            ),
            "raw_products": [],
            "errors": [],
            "execution_time_ms": {},
        }

        result = await agent.execute(state)

        assert result["raw_products"] == []

    @pytest.mark.asyncio
    async def test_execute_no_parsed_query(self):
        """Test execute without parsed query"""
        agent = ScraperAgent()

        state = {
            "stores": [{"name": "Test Store"}],
            "parsed_query": None,
            "raw_products": [],
            "errors": [],
            "execution_time_ms": {},
        }

        result = await agent.execute(state)

        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """Test execute handles errors gracefully"""
        agent = ScraperAgent()

        state = {
            "stores": [{"name": "Bad Store", "website": "https://bad-store-does-not-exist.invalid"}],
            "parsed_query": ParsedQuery(
                brand="Test",
                original_query="test",
                model=None,
                category=None,
                size=None,
                gender=None,
                color=None
            ),
            "raw_products": [],
            "errors": [],
            "execution_time_ms": {},
        }

        result = await agent.execute(state)

        # Should continue despite error
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing agent"""
        agent = ScraperAgent()

        # Should not raise error
        await agent.close()


class TestScraperIntegration:
    """Integration tests for scrapers"""

    def test_product_model_creation(self):
        """Test creating ProductModel with scraper"""
        scraper = GenericScraper("Test", "https://test.com")

        product = scraper._build_product(
            product_id="p1",
            store_id="s1",
            title="Product 1",
            price=99.99,
            url="https://test.com/p1",
            rating=4.5,
            reviews_count=50,
            availability=True,
            specs={"color": "black", "size": "42"}
        )

        assert product.product_id == "p1"
        assert product.title == "Product 1"
        assert product.price == 99.99
        assert product.rating == 4.5
        assert product.reviews_count == 50
        assert product.specs["color"] == "black"

    def test_scraper_error_handling(self):
        """Test scraper error classes"""
        from app.scrapers.base import ScraperError, ScraperTimeoutError, RateLimitError

        error = ScraperError("Test error")
        assert isinstance(error, Exception)

        timeout_error = ScraperTimeoutError("Timeout")
        assert isinstance(timeout_error, ScraperError)

        rate_limit_error = RateLimitError("Rate limited")
        assert isinstance(rate_limit_error, ScraperError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
