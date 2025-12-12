import logging
import re
from typing import Optional, Dict, Any
import httpx

from app.scrapers.base import (
    BaseScraper,
    ScraperError,
    ScraperParseError,
    ScraperTimeoutError,
)

logger = logging.getLogger(__name__)


class GenericScraper(BaseScraper):
    """
    Generic scraper used in test_phase4.
    Tests require the following private-prefixed methods:

    - _validate_product()
    - _build_product()
    - _build_search_url()
    - _parse_price()
    - _get_client()
    - attribute: store_url
    """

    def __init__(self, store_name: str, base_url: str):
        super().__init__(store_name, base_url)
        self.store_url = base_url  # tests expect this
        logger.debug(f"GenericScraper initialized for {store_name}")

    # --------------------------------------------------------------
    # Test-required wrapper around BaseScraper.validate_product()
    # --------------------------------------------------------------
    def _validate_product(self, product: Dict[str, Any]) -> bool:
        return self.validate_product(product)

    # --------------------------------------------------------------
    # Test-required wrapper around BaseScraper.build_product()
    # --------------------------------------------------------------
    def _build_product(self, **kwargs) -> Dict[str, Any]:
        """
        Tests provide product fields like:
        product_id, store_id, title, price, url, rating, etc.
        """
        product = {
            "name": kwargs.get("title"),
            "price": kwargs.get("price"),
            "url": kwargs.get("url"),
            "store": self.store_name,
            "rating": kwargs.get("rating"),
            "reviews_count": kwargs.get("reviews_count"),
            "availability": kwargs.get("availability"),
            "specs": kwargs.get("specs"),
        }

        if not self.validate_product(product):
            raise ScraperParseError("Invalid product structure")

        return product

    # --------------------------------------------------------------
    # Build search URL
    # --------------------------------------------------------------
    def _build_search_url(self, query: str) -> str:
        """
        Tests expect something like:
        https://test.com/search?q=adidas+shoes
        """
        q = query.replace(" ", "+")
        return f"{self.store_url}/search?q={q}"

    # --------------------------------------------------------------
    # Parse a price string
    # --------------------------------------------------------------
    def _parse_price(self, text: str) -> Optional[float]:
        """
        Valid price examples:
        - "$99.99"
        - "99.99 USD"
        - "€120"
        Invalid returns None
        """
        match = re.search(r"([\d]+(?:\.\d+)?)", text)
        if not match:
            return None

        try:
            return float(match.group(1))
        except Exception:
            return None

    # --------------------------------------------------------------
    # HTTP client getter
    # --------------------------------------------------------------
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Tests patch httpx.AsyncClient and expect this method to await.
        """
        return httpx.AsyncClient(timeout=10.0)


# ============================================================
# Factory required by tests
# ============================================================

def create_generic_scraper(store_name: str, base_url: str) -> GenericScraper:
    return GenericScraper(store_name, base_url)
