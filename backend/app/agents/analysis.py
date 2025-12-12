"""
LangGraph Agent Node: Intelligent product analysis and recommendations using Claude AI.

Uses OpenRouter API to analyze matched products and provide recommendations.

Responsibilities:
- Analyze price vs quality trade-offs
- Compare products and ratings
- Consider distance and availability
- Generate recommendations
- Provide structured output with reasoning

Input: SearchState with 'matched_products' and 'parsed_query'
Output: SearchState with 'analysis' field populated
"""

import logging
import time
import json
import asyncio
from typing import Dict, List, Any, Optional
import httpx
from app.services.openrouter import OpenRouterClient
from app.models.schemas import SearchState, AnalysisResult, Recommendation, PriceAnalysis
from app.config import settings

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    LangGraph Agent Node: Analyzes products using Claude AI via OpenRouter.

    Features:
    - Intelligent product analysis
    - Price vs quality comparison
    - Distance considerations
    - Availability checking
    - Structured recommendations
    - Reasoning explanation
    - JSON output parsing
    """

    def __init__(self):
        """Initialize AnalysisAgent with OpenRouter client."""
        self.client = OpenRouterClient()
        logger.info("AnalysisAgent initialized")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze matched products and generate recommendations.

        Args:
            state: SearchState with 'matched_products' field

        Returns:
            Updated state with 'analysis' field
        """
        start_time = time.time()
        logger.info("AnalysisAgent starting")

        try:
            # Get matched products
            matched_products = state.get("matched_products", [])
            if not matched_products:
                logger.warning("No matched products to analyze")
                state["analysis"] = None
                state["execution_time_ms"]["analyze"] = int(
                    (time.time() - start_time) * 1000
                )
                return state

            # Get parsed query for context
            parsed_query = state.get("parsed_query")
            if not parsed_query:
                logger.warning("No parsed query available")
                parsed_query = None

            # Prepare product data for analysis
            products_data = self._prepare_products_for_analysis(matched_products)

            logger.info(f"Analyzing {len(matched_products)} products")

            # Call Claude AI for analysis
            analysis = await self.client.analyze_products(
                products=products_data,
                user_query=parsed_query.original_query if parsed_query else "",
                parsed_query=parsed_query
            )

            if analysis:
                state["analysis"] = analysis
                logger.info("Analysis completed successfully")
            else:
                logger.error("Failed to analyze products")
                state["errors"].append("Product analysis failed")

            # Track execution time
            state["execution_time_ms"]["analyze"] = int(
                (time.time() - start_time) * 1000
            )

            logger.info(f"AnalysisAgent completed in {state['execution_time_ms']['analyze']}ms")

            return state

        except Exception as e:
            error_msg = f"AnalysisAgent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            return state

    def _prepare_products_for_analysis(self, matched_products: List[Any]) -> List[Dict[str, Any]]:
        """
        Prepare product data for Claude analysis.

        Args:
            matched_products: List of MatchedProduct objects

        Returns:
            List of dictionaries with product info
        """
        products = []
        for product in matched_products:
            product_dict = {
                "id": product.product_id,
                "title": product.title,
                "price": product.price,
                "currency": product.currency,
                "rating": product.rating or 0,
                "reviews": product.reviews_count or 0,
                "store": product.store_name,
                "distance_km": product.distance_km,
                "available": product.availability,
                "url": product.url,
                "similarity": round(product.similarity_score * 100, 1),  # Percentage
            }

            if product.specs:
                product_dict["specs"] = product.specs

            products.append(product_dict)

        return products

    async def close(self) -> None:
        """Close connections."""
        await self.client.close()


# Define the async node function for LangGraph
async def analyze_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for product analysis.

    Args:
        state: Current workflow state

    Returns:
        Updated state with analysis
    """
    agent = AnalysisAgent()
    try:
        return await agent.execute(state)
    finally:
        await agent.close()
