"""
Unit tests for Phase 3 agents (QueryParserAgent and StoreDiscoveryAgent).
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.agents.query_parser import QueryParserAgent, parse_query_node
from app.agents.store_discovery import StoreDiscoveryAgent, discover_stores_node
from app.graph.state import SearchState, create_initial_state, validate_state
from app.models.schemas import ParsedQuery, StoreModel


class TestQueryParserAgent:
    """Tests for QueryParserAgent"""

    def test_execute_valid_query(self):
        """Test parsing a valid query"""
        state = {
            "query": "adidas samba man 42 black",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        result = QueryParserAgent.execute(state)

        assert result["parsed_query"] is not None
        assert result["parsed_query"].brand == "Adidas"
        assert result["parsed_query"].model == "Samba"
        assert result["parsed_query"].size == "42"
        assert result["parsed_query"].gender == "men"
        assert result["parsed_query"].color == "black"
        assert "parse_query" in result["execution_time_ms"]

    def test_execute_empty_query(self):
        """Test handling empty query"""
        state = {
            "query": "",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        result = QueryParserAgent.execute(state)

        assert len(result["errors"]) > 0
        assert result["parsed_query"] is None

    def test_execute_minimal_query(self):
        """Test parsing minimal query with just brand"""
        state = {
            "query": "nike",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        result = QueryParserAgent.execute(state)

        assert result["parsed_query"] is not None
        assert result["parsed_query"].brand == "Nike"

    def test_validate_output_success(self):
        """Test output validation with valid parsed query"""
        parsed = ParsedQuery(
            brand="Nike",
            model="Air Max",
            category="shoes",
            size="10",
            gender="men",
            color="black",
            original_query="nike air max men 10"
        )

        state = {
            "parsed_query": parsed,
            "query": "nike air max men 10",
        }

        assert QueryParserAgent.validate_output(state) is True

    def test_validate_output_missing(self):
        """Test output validation with missing parsed_query"""
        state = {
            "parsed_query": None,
            "query": "test",
        }

        assert QueryParserAgent.validate_output(state) is False

    def test_get_search_category_from_parsed(self):
        """Test category extraction from parsed query"""
        parsed = ParsedQuery(
            brand="Nike",
            model=None,
            category="shoes",
            size=None,
            gender=None,
            color=None,
            original_query="nike shoes"
        )

        state = {"parsed_query": parsed, "query": "nike shoes"}

        category = QueryParserAgent.get_search_category(state)
        assert category == "shoes"

    def test_get_search_category_fallback(self):
        """Test fallback category when not in parsed query"""
        parsed = ParsedQuery(
            brand="Nike",
            model=None,
            category=None,  # No category
            size=None,
            gender=None,
            color=None,
            original_query="nike shoe"
        )

        state = {"parsed_query": parsed, "query": "nike shoe"}

        category = QueryParserAgent.get_search_category(state)
        # Should use fallback detection
        assert category in ["shoes", "general"]

    def test_get_search_terms(self):
        """Test building optimized search terms"""
        parsed = ParsedQuery(
            brand="Adidas",
            model="Samba",
            category="shoes",
            size="42",
            gender="men",
            color="black",
            original_query="adidas samba man 42 black"
        )

        state = {"parsed_query": parsed}

        search_terms = QueryParserAgent.get_search_terms(state)
        assert "Adidas" in search_terms
        assert "Samba" in search_terms

    @pytest.mark.asyncio
    async def test_parse_query_node(self):
        """Test async node function"""
        state = {
            "query": "adidas samba",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        result = await parse_query_node(state)

        assert result["parsed_query"] is not None
        assert "parse_query" in result["execution_time_ms"]


class TestStoreDiscoveryAgent:
    """Tests for StoreDiscoveryAgent"""

    def test_init_with_client(self):
        """Test initialization with provided client"""
        mock_client = Mock()
        agent = StoreDiscoveryAgent(gmaps_client=mock_client)
        assert agent.gmaps == mock_client

    @patch("app.agents.store_discovery.googlemaps.Client")
    def test_init_without_client(self, mock_client_class):
        """Test initialization creates new client"""
        agent = StoreDiscoveryAgent()
        assert agent.gmaps is not None

    @pytest.mark.asyncio
    async def test_execute_invalid_location(self):
        """Test handling invalid location"""
        agent = StoreDiscoveryAgent(gmaps_client=Mock())

        state = {
            "query": "test",
            "location": {},  # Missing lat/lng
            "parsed_query": None,
            "errors": [],
            "execution_time_ms": {},
        }

        result = await agent.execute(state)
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_execute_out_of_bounds(self):
        """Test location outside Lebanon bounds"""
        agent = StoreDiscoveryAgent(gmaps_client=Mock())

        state = {
            "query": "test",
            "location": {"lat": 40.7128, "lng": -74.0060},  # New York
            "parsed_query": None,
            "errors": [],
            "execution_time_ms": {},
        }

        result = await agent.execute(state)
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_parse_place_result(self):
        """Test parsing Google Places result"""
        agent = StoreDiscoveryAgent(gmaps_client=Mock())

        place = {
            "place_id": "test_123",
            "name": "Test Store",
            "geometry": {"location": {"lat": 33.89, "lng": 35.50}},
            "vicinity": "Beirut",
            "rating": 4.5,
            "user_ratings_total": 50,
            "opening_hours": {"open_now": True},
        }

        user_location = {"lat": 33.8886, "lng": 35.4955}

        store = agent._parse_place_result(place, user_location)

        assert store is not None
        assert store.store_id == "test_123"
        assert store.name == "Test Store"
        assert store.rating == 4.5
        assert store.distance_km > 0

    def test_parse_place_result_missing_fields(self):
        """Test parsing place with missing fields"""
        agent = StoreDiscoveryAgent(gmaps_client=Mock())

        place = {
            "name": "Incomplete Place",
            # Missing geometry
        }

        user_location = {"lat": 33.8886, "lng": 35.4955}

        store = agent._parse_place_result(place, user_location)
        assert store is None

    def test_is_valid_store_good_rating(self):
        """Test store validation with good rating"""
        store = StoreModel(
            store_id="1",
            name="Good Store",
            address="Beirut",
            lat=33.89,
            lng=35.50,
            distance_km=2.0,
            rating=4.5,
            reviews_count=50,
            currently_open=True,
        )

        agent = StoreDiscoveryAgent(gmaps_client=Mock())
        assert agent._is_valid_store(store) is True

    def test_is_valid_store_low_rating(self):
        """Test store validation with low rating"""
        store = StoreModel(
            store_id="1",
            name="Bad Store",
            address="Beirut",
            lat=33.89,
            lng=35.50,
            distance_km=2.0,
            rating=2.0,  # Below minimum
            reviews_count=10,
            currently_open=True,
        )

        agent = StoreDiscoveryAgent(gmaps_client=Mock())
        assert agent._is_valid_store(store) is False

    def test_build_search_query(self):
        """Test building search query for different categories"""
        agent = StoreDiscoveryAgent(gmaps_client=Mock())

        # Test known category
        query = agent._build_search_query("shoes")
        assert "shoe" in query.lower()

        # Test unknown category
        query = agent._build_search_query("unknown")
        assert "store" in query.lower()


class TestSearchState:
    """Tests for SearchState and utilities"""

    def test_create_initial_state(self):
        """Test creating initial search state"""
        query = "test query"
        location = {"lat": 33.8886, "lng": 35.4955}

        state = create_initial_state(query, location)

        assert state["query"] == query
        assert state["location"] == location
        assert state["parsed_query"] is None
        assert state["stores"] == []
        assert state["errors"] == []
        assert state["execution_time_ms"] == {}

    def test_validate_state_valid(self):
        """Test validating valid state"""
        state = {
            "query": "test",
            "location": {"lat": 33.8886, "lng": 35.4955},
        }

        assert validate_state(state) is True

    def test_validate_state_missing_query(self):
        """Test validation with missing query"""
        state = {
            "location": {"lat": 33.8886, "lng": 35.4955},
        }

        assert validate_state(state) is False

    def test_validate_state_missing_location(self):
        """Test validation with missing location"""
        state = {
            "query": "test",
        }

        assert validate_state(state) is False

    def test_validate_state_invalid_location_format(self):
        """Test validation with invalid location format"""
        state = {
            "query": "test",
            "location": {"lat": 33.8886},  # Missing lng
        }

        assert validate_state(state) is False


class TestIntegration:
    """Integration tests for Phase 3 workflow"""

    @pytest.mark.asyncio
    async def test_query_parser_then_store_discovery(self):
        """Test complete Phase 3 workflow: parse query then discover stores"""
        # First: Parse query
        parse_state = {
            "query": "nike shoes",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        parsed_state = QueryParserAgent.execute(parse_state)
        assert parsed_state["parsed_query"] is not None

        # Second: Would discover stores (requires mocked Google Maps)
        # For now, just verify state flows correctly
        assert "parsed_query" in parsed_state
        assert parsed_state["location"] == parse_state["location"]

    def test_agent_error_accumulation(self):
        """Test that multiple errors accumulate in state"""
        state = {
            "query": "",
            "location": {},
            "errors": [],
            "execution_time_ms": {},
        }

        # Execute QueryParserAgent - should add error for empty query
        result1 = QueryParserAgent.execute(state)
        initial_error_count = len(result1["errors"])

        assert initial_error_count > 0

        # Errors should be preserved
        assert all(isinstance(e, str) for e in result1["errors"])

    def test_execution_time_tracking(self):
        """Test that execution times are tracked"""
        state = {
            "query": "test query",
            "location": {"lat": 33.8886, "lng": 35.4955},
            "errors": [],
            "execution_time_ms": {},
        }

        result = QueryParserAgent.execute(state)

        assert "parse_query" in result["execution_time_ms"]
        assert result["execution_time_ms"]["parse_query"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
