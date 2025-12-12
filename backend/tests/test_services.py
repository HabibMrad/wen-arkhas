import pytest
import math
from app.services.location import LocationService
from app.services.cache import CacheManager
from app.services.query_parser import QueryParser
from app.models.schemas import ParsedQuery


class TestLocationService:
    """Tests for LocationService"""

    def test_calculate_distance_same_point(self):
        """Distance between same points should be 0"""
        point = {"lat": 33.8886, "lng": 35.4955}
        distance = LocationService.calculate_distance(point, point)
        assert distance == 0.0

    def test_calculate_distance_beirut_to_tripoli(self):
        """Test distance calculation between two Lebanese cities"""
        beirut = {"lat": 33.8886, "lng": 35.4955}
        tripoli = {"lat": 34.4325, "lng": 35.8455}
        distance = LocationService.calculate_distance(beirut, tripoli)
        # Approximate distance should be around 60-65 km
        assert 60 <= distance <= 65

    def test_calculate_distance_symmetry(self):
        """Distance should be same in both directions"""
        point1 = {"lat": 33.8886, "lng": 35.4955}
        point2 = {"lat": 34.4325, "lng": 35.8455}
        d1 = LocationService.calculate_distance(point1, point2)
        d2 = LocationService.calculate_distance(point2, point1)
        assert d1 == d2

    def test_validate_location_beirut(self):
        """Valid location in Beirut should pass validation"""
        assert LocationService.validate_location(33.8886, 35.4955) is True

    def test_validate_location_valid_lebanon(self):
        """Valid location in Lebanon bounds should pass"""
        # Tripoli
        assert LocationService.validate_location(34.4325, 35.8455) is True
        # Sidon
        assert LocationService.validate_location(33.5597, 35.3724) is True

    def test_validate_location_outside_bounds(self):
        """Location outside Lebanon should fail validation"""
        # New York
        assert LocationService.validate_location(40.7128, -74.0060) is False
        # Too far south
        assert LocationService.validate_location(32.0, 35.5) is False
        # Too far north
        assert LocationService.validate_location(35.0, 35.5) is False

    def test_validate_location_invalid_type(self):
        """Invalid types should return False"""
        assert LocationService.validate_location("33.8886", "35.4955") is False
        assert LocationService.validate_location(None, 35.4955) is False

    def test_get_search_radius(self):
        """Test search radius bounding box calculation"""
        center = {"lat": 33.8886, "lng": 35.4955}
        radius = LocationService.get_search_radius(center, radius_km=10)

        assert "northeast" in radius
        assert "southwest" in radius
        assert radius["northeast"]["lat"] > center["lat"]
        assert radius["northeast"]["lng"] > center["lng"]
        assert radius["southwest"]["lat"] < center["lat"]
        assert radius["southwest"]["lng"] < center["lng"]

    def test_is_within_radius_true(self):
        """Point within radius should return True"""
        center = {"lat": 33.8886, "lng": 35.4955}
        point = {"lat": 33.9, "lng": 35.5}  # About 1-2 km away
        assert LocationService.is_within_radius(point, center, radius_km=10) is True

    def test_is_within_radius_false(self):
        """Point outside radius should return False"""
        center = {"lat": 33.8886, "lng": 35.4955}
        point = {"lat": 34.4325, "lng": 35.8455}  # ~62 km away
        assert LocationService.is_within_radius(point, center, radius_km=10) is False

    def test_get_city_bounds(self):
        """Test predefined city bounds"""
        beirut = LocationService.get_city_bounds("beirut")
        assert beirut is not None
        assert "center" in beirut
        assert "radius" in beirut

    def test_get_city_bounds_invalid(self):
        """Invalid city should return None"""
        result = LocationService.get_city_bounds("invalid_city")
        assert result is None

    def test_sort_by_distance(self):
        """Test sorting locations by distance"""
        center = {"lat": 33.8886, "lng": 35.4955}
        locations = [
            {"lat": 34.4325, "lng": 35.8455},  # Tripoli (~62 km)
            {"lat": 33.9, "lng": 35.5},         # Very close (~1 km)
            {"lat": 33.5597, "lng": 35.3724},   # Sidon (~35 km)
        ]
        sorted_locs = LocationService.sort_by_distance(locations, center)
        # Closest should be first
        assert sorted_locs[0] == {"lat": 33.9, "lng": 35.5}
        # Furthest should be last
        assert sorted_locs[2] == {"lat": 34.4325, "lng": 35.8455}


class TestCacheManager:
    """Tests for CacheManager"""

    @pytest.fixture
    def cache_manager(self):
        """Create cache manager instance"""
        # Note: Requires Redis running on localhost:6379
        # For testing without Redis, mock the client
        manager = CacheManager()
        if manager.client:
            yield manager
            # Cleanup after test
            asyncio.run(manager.flush_all())
        else:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_is_connected(self, cache_manager):
        """Test Redis connection status"""
        if cache_manager.client:
            assert cache_manager._is_connected() is True

    @pytest.mark.asyncio
    async def test_set_and_get_stores(self, cache_manager):
        """Test caching and retrieving stores"""
        key = CacheManager.generate_key("stores", "33.8886", "35.4955", "shoes")
        stores = [
            {"id": "1", "name": "Store 1", "distance": 1.5},
            {"id": "2", "name": "Store 2", "distance": 3.2},
        ]

        # Set cache
        success = await cache_manager.set_stores(key, stores)
        if success:
            # Get from cache
            cached = await cache_manager.get_stores(key)
            assert cached == stores

    @pytest.mark.asyncio
    async def test_set_and_get_products(self, cache_manager):
        """Test caching and retrieving products"""
        key = CacheManager.generate_key("products", "store_1", "query_hash")
        products = [
            {"id": "p1", "title": "Product 1", "price": 100},
            {"id": "p2", "title": "Product 2", "price": 150},
        ]

        success = await cache_manager.set_products(key, products)
        if success:
            cached = await cache_manager.get_products(key)
            assert cached == products

    @pytest.mark.asyncio
    async def test_set_and_get_search(self, cache_manager):
        """Test caching and retrieving search results"""
        key = CacheManager.generate_key("33.8886", "35.4955", "adidas shoes")
        result = {
            "stores_found": 5,
            "products_found": 25,
            "results": []
        }

        success = await cache_manager.set_search(key, result)
        if success:
            cached = await cache_manager.get_search(key)
            assert cached == result

    @pytest.mark.asyncio
    async def test_generate_key(self):
        """Test cache key generation"""
        key = CacheManager.generate_key("stores", "33.8886", "35.4955", "shoes")
        assert key == "stores:33.8886:35.4955:shoes"

    @pytest.mark.asyncio
    async def test_generate_hash(self):
        """Test hash generation for queries"""
        hash1 = CacheManager.generate_hash("adidas samba")
        hash2 = CacheManager.generate_hash("adidas samba")
        hash3 = CacheManager.generate_hash("nike shoe")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash

    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Test deleting cache entries"""
        key = CacheManager.generate_key("test", "key")
        stores = [{"id": "1", "name": "Test"}]

        await cache_manager.set_stores(key, stores)
        success = await cache_manager.delete(key)

        if success:
            cached = await cache_manager.get_stores(key)
            assert cached is None


class TestQueryParser:
    """Tests for QueryParser"""

    def test_parse_adidas_shoe_query(self):
        """Test parsing Adidas shoe query"""
        query = "adidas Samba man 42 black"
        parsed = QueryParser.parse(query)

        assert parsed.brand == "Adidas"
        assert parsed.model == "Samba"
        assert parsed.gender == "men"
        assert parsed.size == "42"
        assert parsed.color == "black"

    def test_parse_nike_query(self):
        """Test parsing Nike query"""
        query = "nike air max women size 8 white"
        parsed = QueryParser.parse(query)

        assert parsed.brand == "Nike"
        assert parsed.gender == "women"
        assert parsed.size == "8"
        assert parsed.color == "white"

    def test_parse_minimal_query(self):
        """Test parsing minimal query with just brand"""
        query = "adidas"
        parsed = QueryParser.parse(query)

        assert parsed.brand == "Adidas"
        assert parsed.original_query == "adidas"

    def test_extract_brand(self):
        """Test brand extraction"""
        assert QueryParser._extract_brand("adidas samba") == "Adidas"
        assert QueryParser._extract_brand("nike shoes") == "Nike"
        assert QueryParser._extract_brand("random query") is None

    def test_extract_category(self):
        """Test category extraction"""
        assert QueryParser._extract_category("adidas shoe") == "shoes"
        assert QueryParser._extract_category("nike sneaker") == "shoes"
        assert QueryParser._extract_category("samsung phone") == "electronics"
        assert QueryParser._extract_category("blue shirt") == "clothing"

    def test_extract_gender(self):
        """Test gender extraction"""
        assert QueryParser._extract_gender("men shoes") == "men"
        assert QueryParser._extract_gender("women shirt") == "women"
        assert QueryParser._extract_gender("unisex sweater") == "unisex"
        assert QueryParser._extract_gender("no gender") is None

    def test_extract_color(self):
        """Test color extraction"""
        assert QueryParser._extract_color("black shoe") == "black"
        assert QueryParser._extract_color("white shirt") == "white"
        assert QueryParser._extract_color("blue jeans") == "blue"
        assert QueryParser._extract_color("no color") is None

    def test_extract_size(self):
        """Test size extraction"""
        assert QueryParser._extract_size("size 42", "shoes") == "42"
        assert QueryParser._extract_size("size m", "clothing") == "m"
        assert QueryParser._extract_size("no size", None) is None

    def test_normalize_query(self):
        """Test query normalization"""
        query = "  AdIdAs   SaMbA   "
        normalized = QueryParser.normalize_query(query)
        assert normalized == "adidas samba"

    def test_build_search_terms(self):
        """Test building search terms from parsed query"""
        parsed = ParsedQuery(
            brand="Adidas",
            model="Samba",
            category="shoes",
            size="42",
            gender="men",
            color="black",
            original_query="adidas samba man 42 black"
        )
        search_terms = QueryParser.build_search_terms(parsed)
        assert "Adidas" in search_terms
        assert "Samba" in search_terms
        assert "42" in search_terms
        assert "black" in search_terms

    def test_get_fallback_category(self):
        """Test fallback category determination"""
        assert QueryParser.get_fallback_category("shoe") == "shoes"
        assert QueryParser.get_fallback_category("laptop") == "electronics"
        assert QueryParser.get_fallback_category("shirt") == "clothing"
        assert QueryParser.get_fallback_category("watch") == "accessories"
        assert QueryParser.get_fallback_category("random") == "general"

    def test_parse_complex_query(self):
        """Test parsing complex natural language query"""
        query = "I'm looking for red adidas running shoes size 10 for men"
        parsed = QueryParser.parse(query)

        assert parsed.brand == "Adidas"
        assert parsed.gender == "men"
        assert parsed.size == "10"
        assert parsed.color == "red"

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive"""
        query1 = "ADIDAS SAMBA"
        query2 = "adidas samba"
        parsed1 = QueryParser.parse(query1)
        parsed2 = QueryParser.parse(query2)

        assert parsed1.brand == parsed2.brand
        assert parsed1.model == parsed2.model


# For running tests
import asyncio

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
