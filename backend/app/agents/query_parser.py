import logging
import time
from typing import Dict, Any
from app.services.query_parser import QueryParser
from app.models.schemas import SearchState, ParsedQuery

logger = logging.getLogger(__name__)


class QueryParserAgent:
    """
    LangGraph Agent Node: Parses natural language product queries
    into structured data for downstream processing.

    Input: SearchState with 'query' and 'location'
    Output: SearchState with 'parsed_query' field populated
    """

    @staticmethod
    def execute(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user query into structured components.

        Args:
            state: SearchState dict with 'query' key

        Returns:
            Updated state with 'parsed_query' and execution time
        """
        start_time = time.time()
        logger.info(f"QueryParserAgent starting - Query: {state.get('query')}")

        try:
            query = state.get("query", "").strip()

            if not query:
                error_msg = "Query is empty"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Parse query using QueryParser service
            parsed = QueryParser.parse(query)

            logger.debug(f"Parsed query - Brand: {parsed.brand}, "
                        f"Model: {parsed.model}, Category: {parsed.category}, "
                        f"Size: {parsed.size}, Gender: {parsed.gender}, "
                        f"Color: {parsed.color}")

            # Update state with parsed query
            state["parsed_query"] = parsed

            # Track execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            state["execution_time_ms"]["parse_query"] = execution_time_ms

            logger.info(f"QueryParserAgent completed in {execution_time_ms}ms")

            return state

        except Exception as e:
            error_msg = f"QueryParserAgent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            return state

    @staticmethod
    def validate_output(state: Dict[str, Any]) -> bool:
        """
        Validate that parsing was successful.

        Args:
            state: SearchState dict

        Returns:
            True if parsed_query is present and valid
        """
        parsed = state.get("parsed_query")
        if parsed is None:
            logger.warning("QueryParserAgent: parsed_query is None")
            return False

        # At minimum, original query should be present
        if not parsed.original_query:
            logger.warning("QueryParserAgent: original_query is missing")
            return False

        logger.debug("QueryParserAgent validation successful")
        return True

    @staticmethod
    def get_search_category(state: Dict[str, Any]) -> str:
        """
        Get search category from parsed query or use fallback.

        Args:
            state: SearchState dict with parsed_query

        Returns:
            Category string for store discovery
        """
        parsed = state.get("parsed_query")
        if not parsed:
            # Fallback to query-based detection
            query = state.get("query", "")
            return QueryParser.get_fallback_category(query)

        # Use detected category if available
        if parsed.category:
            return parsed.category

        # Otherwise fallback
        return QueryParser.get_fallback_category(parsed.original_query)

    @staticmethod
    def get_search_terms(state: Dict[str, Any]) -> str:
        """
        Get optimized search terms for web scraping.

        Args:
            state: SearchState dict with parsed_query

        Returns:
            Optimized search string
        """
        parsed = state.get("parsed_query")
        if not parsed:
            return state.get("query", "")

        return QueryParser.build_search_terms(parsed)


# Define the node function for LangGraph
async def parse_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for query parsing.

    This is the async wrapper that LangGraph will call.

    Args:
        state: Current workflow state

    Returns:
        Updated state with parsed_query
    """
    return QueryParserAgent.execute(state)
