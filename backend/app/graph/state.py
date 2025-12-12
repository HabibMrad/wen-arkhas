"""
LangGraph workflow state definition.

Defines the SearchState TypedDict which flows through all agent nodes.
"""

from typing import TypedDict, List, Dict, Optional
from app.models.schemas import (
    ParsedQuery,
    StoreModel,
    ProductModel,
    MatchedProduct,
    AnalysisResult,
)


class SearchState(TypedDict, total=False):
    """
    Complete workflow state that flows through all LangGraph nodes.

    Fields:
        query: Original user search query
        location: User location {lat, lng}
        parsed_query: Extracted query components
        stores: Discovered nearby stores
        raw_products: Scraped products (before matching)
        matched_products: Products after semantic matching
        analysis: LLM analysis and recommendations
        errors: Accumulated error messages
        execution_time_ms: Node execution times
    """

    # Input fields
    query: str
    location: Dict[str, float]

    # Processing results
    parsed_query: Optional[ParsedQuery]
    stores: List[Dict]  # List of StoreModel dicts
    raw_products: List[Dict]  # List of ProductModel dicts
    matched_products: List[Dict]  # List of MatchedProduct dicts

    # Output
    analysis: Optional[Dict]  # AnalysisResult dict

    # Metadata
    errors: List[str]
    execution_time_ms: Dict[str, int]


def create_initial_state(query: str, location: Dict[str, float]) -> SearchState:
    """
    Create initial search state.

    Args:
        query: User search query
        location: User location {lat, lng}

    Returns:
        Initial SearchState with all fields set
    """
    return SearchState(
        query=query,
        location=location,
        parsed_query=None,
        stores=[],
        raw_products=[],
        matched_products=[],
        analysis=None,
        errors=[],
        execution_time_ms={},
    )


def validate_state(state: SearchState) -> bool:
    """
    Basic validation of state structure.

    Args:
        state: SearchState to validate

    Returns:
        True if state is valid
    """
    required_fields = ["query", "location"]
    for field in required_fields:
        if field not in state:
            return False

    if not isinstance(state.get("location"), dict):
        return False

    if "lat" not in state["location"] or "lng" not in state["location"]:
        return False

    return True
