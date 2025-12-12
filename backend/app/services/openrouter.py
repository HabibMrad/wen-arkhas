"""
OpenRouter API client for Claude AI integration.

Provides:
- Claude Sonnet 4 for product analysis
- Fallback to GPT-4o if Claude unavailable
- Structured JSON output
- Error handling and retries
"""

import logging
import json
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.models.schemas import AnalysisResult, Recommendation, PriceAnalysis

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """
    Client for OpenRouter API with Claude AI support.

    Features:
    - Uses Claude Sonnet 4 for analysis
    - Fallback to GPT-4o
    - Structured JSON output
    - Retry logic for robustness
    - Cost tracking via logging
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (default from settings)
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://wen-arkhas.app",
                "X-Title": "Wen-Arkhas",
            }
        )
        logger.info("OpenRouterClient initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def analyze_products(
        self,
        products: List[Dict[str, Any]],
        user_query: str,
        parsed_query: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze products using Claude AI.

        Args:
            products: List of product data
            user_query: Original user query
            parsed_query: Parsed query object

        Returns:
            Analysis result dictionary or None
        """
        try:
            logger.info(f"Analyzing {len(products)} products with Claude AI")

            # Build prompt
            prompt = self._build_analysis_prompt(products, user_query, parsed_query)

            # Call Claude API
            response = await self._call_claude(prompt)

            if response:
                logger.info("Product analysis completed")
                return response
            else:
                logger.error("Claude API returned empty response")
                return None

        except Exception as e:
            logger.error(f"Error analyzing products: {str(e)}")
            raise

    def _build_analysis_prompt(
        self,
        products: List[Dict[str, Any]],
        user_query: str,
        parsed_query: Optional[Any] = None
    ) -> str:
        """
        Build analysis prompt for Claude.

        Args:
            products: Product data
            user_query: User query
            parsed_query: Parsed query object

        Returns:
            Prompt string
        """
        prompt = f"""You are an expert product recommendation assistant for a price comparison platform.

Analyze the following products based on the user's search query and provide intelligent recommendations.

USER QUERY: {user_query}

PRODUCTS TO ANALYZE:
"""
        for i, product in enumerate(products, 1):
            prompt += f"""
{i}. {product['title']}
   - Price: {product['price']} {product['currency']}
   - Rating: {product['rating']}/5.0 ({product['reviews']} reviews)
   - Store: {product['store']} ({product['distance_km']}km away)
   - Available: {'Yes' if product['available'] else 'No'}
   - Match Score: {product.get('similarity', 'N/A')}%
   - URL: {product['url']}
"""
            if product.get('specs'):
                prompt += f"   - Specs: {json.dumps(product['specs'])}\n"

        prompt += """

ANALYSIS INSTRUCTIONS:
1. Analyze price vs quality trade-offs
2. Consider distance to store and delivery implications
3. Evaluate product availability
4. Compare ratings and customer reviews
5. Identify best value options
6. Consider relevance to original query
7. Rank top 3 recommendations

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
  "best_value": {
    "product_id": "id of the best value product",
    "reasoning": "why this represents the best value"
  },
  "top_3_recommendations": [
    {
      "rank": 1,
      "product_id": "product id",
      "category": "best_value | best_rating | closest | best_overall",
      "pros": ["pro 1", "pro 2"],
      "cons": ["con 1", "con 2"]
    }
  ],
  "price_analysis": {
    "min_price": minimum price found,
    "max_price": maximum price found,
    "average_price": average price,
    "median_price": median price
  },
  "summary": "2-3 sentence summary of recommendations"
}

Only return valid JSON, no additional text."""

        return prompt

    async def _call_claude(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Call Claude API via OpenRouter.

        Args:
            prompt: Analysis prompt

        Returns:
            Parsed response or None
        """
        try:
            logger.debug("Calling Claude API via OpenRouter")

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": settings.default_model,  # anthropic/claude-sonnet-4-20250514
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract content
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                logger.debug(f"Claude response: {content[:200]}...")

                # Log token usage for cost tracking
                usage = data.get("usage", {})
                logger.info(
                    f"API call - Input: {usage.get('prompt_tokens')}, "
                    f"Output: {usage.get('completion_tokens')}"
                )

                # Parse JSON
                try:
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
                    logger.debug(f"Response content: {content}")
                    return None
            else:
                logger.error("Unexpected API response format")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Claude API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.debug("Closed OpenRouter client")

    def __repr__(self) -> str:
        return f"<OpenRouterClient model={settings.default_model}>"
