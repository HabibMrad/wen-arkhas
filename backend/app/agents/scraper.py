"""
LangGraph Agent Node: Scrapes product listings from store websites.

Responsibilities:
- Find appropriate scraper for each store
- Scrape products from store websites
- Handle rate limiting (1 req/sec per domain)
- Cache results (6 hours)
- Handle errors and retries

Input: SearchState with 'stores' field
Output: SearchState with 'raw_products' field populated
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from app.scrapers.generic import GenericScraper
from app.scrapers.playwright import PlaywrightScraper
from app.services.cache import CacheManager
from app.models.schemas import SearchState, ProductModel
from app.config import settings

logger = logging.getLogger(__name__)


class ScraperAgent:
    """
    LangGraph Agent Node: Scrapes products from discovered stores.

    Uses appropriate scraper for each store:
    - GenericScraper for static HTML sites
    - PlaywrightScraper for JavaScript-heavy sites

    Input: SearchState with 'stores' list
    Output: SearchState with 'raw_products' list
    """

    # Mapping of domain patterns to scraper preferences
    SCRAPER_PREFERENCES = {
        "nike": "playwright",      # React site
        "adidas": "generic",       # Mostly static
        "amazon": "playwright",    # Dynamic content
        "ebay": "generic",         # Mostly static
        "zalando": "playwright",   # Heavy JavaScript
        "asos": "playwright",      # React site
    }

    def __init__(self):
        """Initialize ScraperAgent."""
        self.cache = CacheManager()
        self.active_scrapers = {}
        logger.info("ScraperAgent initialized")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape products from all discovered stores.

        Args:
            state: SearchState with 'stores' field

        Returns:
            Updated state with 'raw_products' field
        """
        start_time = time.time()
        logger.info("ScraperAgent starting")

        try:
            stores = state.get("stores", [])
            if not stores:
                logger.warning("No stores to scrape")
                state["raw_products"] = []
                return state

            parsed_query = state.get("parsed_query")
            if not parsed_query:
                error_msg = "No parsed query available"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Build search terms
            search_terms = self._build_search_terms(parsed_query)
            logger.debug(f"Search terms: {search_terms}")

            # Scrape products from each store
            all_products = []
            for store in stores:
                try:
                    store_id = store.get("store_id") or store.get("name")
                    logger.info(f"Scraping {store.get('name')}")

                    # Check cache
                    cache_key = self._get_cache_key(store_id, search_terms)
                    cached_products = await self.cache.get_products(cache_key)
                    if cached_products:
                        logger.info(f"Cache hit for {store.get('name')}")
                        products = [ProductModel(**p) for p in cached_products]
                        all_products.extend(products)
                        continue

                    # Scrape products
                    products = await self._scrape_store(
                        store,
                        search_terms,
                        store_id
                    )

                    if products:
                        logger.info(f"Scraped {len(products)} from {store.get('name')}")
                        all_products.extend(products)

                        # Cache results (6h)
                        product_dicts = [p.dict(exclude_unset=True) for p in products]
                        await self.cache.set_products(
                            cache_key,
                            product_dicts,
                            ttl_hours=settings.cache_ttl_products_hours
                        )
                    else:
                        logger.warning(f"No products scraped from {store.get('name')}")

                except Exception as e:
                    error_msg = f"Error scraping {store.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    state["errors"].append(error_msg)
                    continue

            state["raw_products"] = all_products

            # Track execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            state["execution_time_ms"]["scrape_products"] = execution_time_ms

            logger.info(f"ScraperAgent completed in {execution_time_ms}ms")
            logger.info(f"Total products scraped: {len(all_products)}")

            return state

        except Exception as e:
            error_msg = f"ScraperAgent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            return state

    async def _scrape_store(
        self,
        store: Dict[str, Any],
        search_terms: str,
        store_id: str
    ) -> List[ProductModel]:
        """
        Scrape products from a single store.

        Args:
            store: Store information
            search_terms: Optimized search terms
            store_id: Unique store identifier

        Returns:
            List of ProductModel objects
        """
        try:
            # Get store URL
            store_url = store.get("website") or store.get("url")
            if not store_url:
                logger.warning(f"No URL available for store: {store.get('name')}")
                return []

            # Determine scraper type
            scraper_type = self._get_scraper_type(store_url)

            # Create scraper
            if scraper_type == "playwright":
                scraper = PlaywrightScraper(store.get("name"), store_url)
            else:
                scraper = GenericScraper(store.get("name"), store_url)

            try:
                # Scrape products
                products = await scraper.scrape_search(
                    search_terms,
                    search_url=store_url  # Could be enhanced
                )

                # Add store information to products
                for product in products:
                    product.store_id = store_id

                return products

            finally:
                await scraper.aclose()

        except Exception as e:
            logger.error(f"Error scraping store: {str(e)}")
            return []

    def _get_scraper_type(self, store_url: str) -> str:
        """
        Determine which scraper to use for a store.

        Args:
            store_url: Store URL

        Returns:
            "playwright" or "generic"
        """
        # Check preferences
        for domain, preference in self.SCRAPER_PREFERENCES.items():
            if domain in store_url.lower():
                return preference

        # Default to generic for unknown stores
        return "generic"

    def _build_search_terms(self, parsed_query) -> str:
        """
        Build search terms from parsed query.

        Args:
            parsed_query: ParsedQuery object

        Returns:
            Search terms string
        """
        terms = []

        if parsed_query.brand:
            terms.append(parsed_query.brand)
        if parsed_query.model:
            terms.append(parsed_query.model)
        if parsed_query.color:
            terms.append(parsed_query.color)
        if parsed_query.size:
            terms.append(str(parsed_query.size))

        return " ".join(terms) if terms else parsed_query.original_query

    def _get_cache_key(self, store_id: str, search_terms: str) -> str:
        """
        Get cache key for products.

        Args:
            store_id: Store identifier
            search_terms: Search terms

        Returns:
            Cache key
        """
        query_hash = CacheManager.generate_hash(search_terms)
        return CacheManager.generate_key("products", store_id, query_hash)

    async def close(self) -> None:
        """Close all active scrapers."""
        for scraper in self.active_scrapers.values():
            try:
                await scraper.aclose()
            except Exception as e:
                logger.warning(f"Error closing scraper: {str(e)}")
        self.active_scrapers.clear()


# Define the async node function for LangGraph
async def scrape_products_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for product scraping.

    Args:
        state: Current workflow state

    Returns:
        Updated state with raw_products
    """
    agent = ScraperAgent()
    try:
        return await agent.execute(state)
    finally:
        await agent.close()
