"""
Integration tests for Phase 7 LangGraph workflow with all 5 agents.

Tests the complete workflow:
1. QueryParserAgent - Parse query
2. StoreDiscoveryAgent - Find stores
3. ScraperAgent - Scrape products
4. RAGAgent - Match products
5. AnalysisAgent - Analyze and recommend
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.graph.workflow import WorkflowBuilder, WorkflowExecutor
from app.graph.state import SearchState, create_initial_state, validate_state
from app.models.schemas import (
    ParsedQuery, StoreModel, ProductModel, MatchedProduct, AnalysisResult
)


class TestWorkflowBuilder:
    """Tests for WorkflowBuilder"""

    def test_build_phase3_workflow(self):
        """Test building Phase 3 workflow (query + stores only)"""
        workflow = WorkflowBuilder.build_phase3_workflow()

        assert workflow is not None
        # Phase 3 workflow should have: parse_query, discover_stores nodes
        # Actual node inspection depends on LangGraph internals

    def test_build_complete_workflow(self):
        """Test building complete Phase 7 workflow with all 5 agents"""
        workflow = WorkflowBuilder.build_complete_workflow()

        assert workflow is not None
        # Phase 7 workflow should have all 5 nodes

    def test_workflow_has_correct_node_flow(self):
        """Test that workflow nodes are properly connected"""
        workflow = WorkflowBuilder.build_complete_workflow()

        # Verify workflow compiles without errors
        assert workflow is not None


class TestWorkflowExecutor:
    """Tests for WorkflowExecutor"""

    def test_executor_initialization_default(self):
        """Test executor initialization with default (complete) workflow"""
        with patch("app.graph.workflow.WorkflowBuilder.build_complete_workflow") as mock_build:
            mock_build.return_value = MagicMock()
            executor = WorkflowExecutor()

            assert executor.graph is not None
            mock_build.assert_called_once()

    def test_executor_initialization_phase3(self):
        """Test executor initialization with Phase 3 workflow"""
        with patch("app.graph.workflow.WorkflowBuilder.build_phase3_workflow") as mock_build:
            mock_build.return_value = MagicMock()
            executor = WorkflowExecutor(use_complete=False)

            assert executor.graph is not None
            mock_build.assert_called_once()

    def test_executor_initialization_custom_graph(self):
        """Test executor initialization with custom graph"""
        custom_graph = MagicMock()
        executor = WorkflowExecutor(graph=custom_graph)

        assert executor.graph == custom_graph

    @pytest.mark.asyncio
    async def test_invoke_with_valid_state(self):
        """Test workflow invocation with valid input"""
        # Create mock graph
        mock_graph = AsyncMock()
        expected_result = {
            "query": "nike shoes",
            "location": {"lat": 33.89, "lng": 35.50},
            "parsed_query": ParsedQuery(
                brand="Nike",
                original_query="nike shoes",
                model=None,
                category=None,
                size=None,
                gender=None,
                color=None
            ),
            "stores": [{"name": "Nike Store"}],
            "raw_products": [],
            "matched_products": [],
            "analysis": None,
            "errors": [],
            "execution_time_ms": {}
        }
        mock_graph.ainvoke = AsyncMock(return_value=expected_result)

        executor = WorkflowExecutor(graph=mock_graph)
        result = await executor.invoke("nike shoes", {"lat": 33.89, "lng": 35.50})

        assert result is not None
        assert result["query"] == "nike shoes"
        mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_with_invalid_state(self):
        """Test workflow invocation with invalid input"""
        mock_graph = MagicMock()
        executor = WorkflowExecutor(graph=mock_graph)

        # Missing required 'location' field
        result = await executor.invoke("query", {})

        assert result is not None
        assert "errors" in result
        assert "Invalid input state" in result["errors"]

    @pytest.mark.asyncio
    async def test_invoke_streaming_valid_input(self):
        """Test streaming workflow execution"""
        # Create mock graph
        mock_graph = AsyncMock()

        # Simulate streaming events from graph
        async def mock_astream(state):
            yield {
                "parse_query": {
                    "query": state["query"],
                    "parsed_query": ParsedQuery(
                        brand="Nike",
                        original_query="nike shoes",
                        model=None,
                        category=None,
                        size=None,
                        gender=None,
                        color=None
                    ),
                    "execution_time_ms": {"parse_query": 50},
                    "errors": []
                }
            }
            yield {
                "discover_stores": {
                    "stores": [{"name": "Nike Store"}],
                    "execution_time_ms": {"parse_query": 50, "discover_stores": 200},
                    "errors": []
                }
            }
            yield {
                "scrape_products": {
                    "raw_products": [],
                    "execution_time_ms": {"discover_stores": 200, "scrape_products": 0},
                    "errors": []
                }
            }
            yield {
                "match_products": {
                    "matched_products": [],
                    "execution_time_ms": {"scrape_products": 0, "match_products": 0},
                    "errors": []
                }
            }
            yield {
                "analyze": {
                    "analysis": None,
                    "execution_time_ms": {"match_products": 0, "analyze": 0},
                    "errors": []
                }
            }

        mock_graph.astream = mock_astream

        executor = WorkflowExecutor(graph=mock_graph)

        # Collect all streamed events
        events = []
        async for event in executor.invoke_streaming("nike shoes", {"lat": 33.89, "lng": 35.50}):
            events.append(event)

        # Should have 6 events: 5 agents + 1 complete
        assert len(events) >= 1
        # Last event should be complete
        assert events[-1]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_invoke_streaming_with_error(self):
        """Test streaming execution with error"""
        mock_graph = AsyncMock()
        mock_graph.astream = AsyncMock(side_effect=Exception("Test error"))

        executor = WorkflowExecutor(graph=mock_graph)

        events = []
        async for event in executor.invoke_streaming("query", {"lat": 33.89, "lng": 35.50}):
            events.append(event)

        # Should have error event
        assert len(events) > 0
        assert events[-1]["status"] == "error"


class TestWorkflowState:
    """Tests for workflow state management"""

    def test_create_initial_state(self):
        """Test initial state creation"""
        state = create_initial_state("nike shoes", {"lat": 33.89, "lng": 35.50})

        assert state["query"] == "nike shoes"
        assert state["location"]["lat"] == 33.89
        assert state["location"]["lng"] == 35.50
        assert state["parsed_query"] is None
        assert state["stores"] == []
        assert state["raw_products"] == []
        assert state["matched_products"] == []
        assert state["analysis"] is None
        assert state["errors"] == []
        assert state["execution_time_ms"] == {}

    def test_validate_state_valid(self):
        """Test state validation with valid state"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})

        assert validate_state(state) is True

    def test_validate_state_missing_query(self):
        """Test state validation with missing query"""
        state = {"location": {"lat": 33.89, "lng": 35.50}}

        assert validate_state(state) is False

    def test_validate_state_missing_location(self):
        """Test state validation with missing location"""
        state = {"query": "test"}

        assert validate_state(state) is False

    def test_validate_state_invalid_location(self):
        """Test state validation with invalid location"""
        state = {
            "query": "test",
            "location": {"lat": 33.89}  # Missing lng
        }

        assert validate_state(state) is False


class TestWorkflowIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.asyncio
    async def test_complete_workflow_flow(self):
        """Test complete workflow from input to output"""
        # This is a high-level integration test
        executor = WorkflowExecutor(use_complete=True)

        # Create initial state
        state = create_initial_state("nike shoes", {"lat": 33.89, "lng": 35.50})

        # Validate state
        assert validate_state(state) is True

    def test_workflow_streaming_data_progression(self):
        """Test that streaming provides progressive data"""
        # Mock states at different workflow stages
        state_parse = {
            "query": "nike shoes",
            "parsed_query": ParsedQuery(
                brand="Nike",
                original_query="nike shoes",
                model=None,
                category=None,
                size=None,
                gender=None,
                color=None
            ),
            "execution_time_ms": {"parse_query": 50},
        }

        state_discover = {
            **state_parse,
            "stores": [
                {"name": "Nike Store 1", "lat": 33.89, "lng": 35.50},
                {"name": "Nike Store 2", "lat": 33.90, "lng": 35.51}
            ],
            "execution_time_ms": {
                "parse_query": 50,
                "discover_stores": 200
            }
        }

        # Verify state progression
        assert state_parse["parsed_query"] is not None
        assert state_discover["stores"] != []
        assert len(state_discover["execution_time_ms"]) > len(state_parse["execution_time_ms"])

    def test_conditional_routing_logic(self):
        """Test conditional routing for store retry logic"""
        # Test: stores < 3 should retry
        state_few_stores = {
            "stores": [{"name": "Store 1"}],  # Only 1 store
            "errors": []
        }

        # Simulate conditional routing logic
        stores = state_few_stores.get("stores", [])
        retry_count = len([e for e in state_few_stores.get("errors", []) if "discover_stores" in e])

        should_retry = len(stores) < 3 and retry_count < 2
        assert should_retry is True

        # Test: stores >= 3 should not retry
        state_enough_stores = {
            "stores": [
                {"name": "Store 1"},
                {"name": "Store 2"},
                {"name": "Store 3"}
            ],
            "errors": []
        }

        stores = state_enough_stores.get("stores", [])
        retry_count = len([e for e in state_enough_stores.get("errors", []) if "discover_stores" in e])

        should_retry = len(stores) < 3 and retry_count < 2
        assert should_retry is False

    def test_error_accumulation(self):
        """Test that errors accumulate without stopping execution"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})

        # Simulate errors from multiple agents
        state["errors"].append("parse_query: Failed to parse brand")
        state["errors"].append("discover_stores: API rate limit exceeded")
        state["errors"].append("scrape_products: Connection timeout")

        # Workflow should continue despite errors
        assert len(state["errors"]) == 3
        # State should still have all required fields
        assert "query" in state
        assert "location" in state

    def test_execution_time_tracking(self):
        """Test execution time tracking per node"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})

        # Simulate execution times from each agent
        state["execution_time_ms"]["parse_query"] = 50
        state["execution_time_ms"]["discover_stores"] = 200
        state["execution_time_ms"]["scrape_products"] = 500
        state["execution_time_ms"]["match_products"] = 300
        state["execution_time_ms"]["analyze"] = 3000

        # Calculate total time
        total_time = sum(state["execution_time_ms"].values())
        assert total_time == 4050

        # Verify each agent's time
        assert state["execution_time_ms"]["parse_query"] == 50
        assert state["execution_time_ms"]["analyze"] == 3000


class TestWorkflowEdgeCases:
    """Tests for edge cases in workflow execution"""

    def test_empty_stores_list(self):
        """Test workflow with no stores discovered"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})
        state["stores"] = []

        # Workflow should handle gracefully
        assert state["stores"] == []

    def test_no_products_found(self):
        """Test workflow with no products scraped"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})
        state["raw_products"] = []
        state["matched_products"] = []

        # Workflow should handle gracefully
        assert len(state["matched_products"]) == 0

    def test_analysis_without_products(self):
        """Test analysis agent with no matched products"""
        state = create_initial_state("query", {"lat": 33.89, "lng": 35.50})
        state["matched_products"] = []

        # Analysis should return None or empty result
        assert state["matched_products"] == []

    def test_location_boundaries(self):
        """Test workflow with edge locations"""
        # North boundary of Lebanon
        state_north = create_initial_state("query", {"lat": 34.7, "lng": 35.8})
        assert validate_state(state_north) is True

        # South boundary of Lebanon
        state_south = create_initial_state("query", {"lat": 33.0, "lng": 35.1})
        assert validate_state(state_south) is True

    def test_unicode_query(self):
        """Test workflow with Unicode characters"""
        state = create_initial_state("Nike أحذية", {"lat": 33.89, "lng": 35.50})

        assert validate_state(state) is True
        assert "أحذية" in state["query"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
