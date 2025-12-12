import abc
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================================
# Exceptions required by tests
# ============================================================

class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class ScraperParseError(ScraperError):
    """Raised when the scraper cannot parse product data."""
    pass


class ScraperTimeoutError(ScraperError):
    """Raised when scraping exceeds the allowed time."""
    pass

class RateLimitError(ScraperError):
    """Raised when store blocks or rate-limits scraping."""
    pass

# ============================================================
# BaseScraper (required by all tests)
# ============================================================

class BaseScraper(abc.ABC):
    """
    Abstract base class for all scrapers.
    Tests require:
    - store_name
    - base_url
    - validate_product()
    - build_product()
    - get_store_id()
    """

    def __init__(self, store_name: str, base_url: str):
        self.store_name = store_name
        self.base_url = base_url
        logger.debug(f"Initialized BaseScraper for {store_name}")

    # ------------------------
    # Required abstract method
    # ------------------------
    @abc.abstractmethod
    def _parse_product(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a raw product dictionary into normalized fields."""
        raise NotImplementedError

    # ------------------------
    # Provided helpers
    # ------------------------
    def validate_product(self, product: Dict[str, Any]) -> bool:
        """Validate product data."""
        if "name" not in product or not product["name"]:
            return False

        if "price" not in product:
            return False

        try:
            if float(product["price"]) <= 0:
                return False
        except Exception:
            return False

        return True

    def build_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize product."""
        if not self.validate_product(product):
            raise ScraperParseError("Invalid product structure")

        return {
            "name": product["name"],
            "price": float(product["price"]),
            "url": product.get("url", ""),
            "store": self.store_name,
        }

    def get_store_id(self) -> str:
        """Convert URL to domain id."""
        try:
            domain = (
                self.base_url.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .lower()
            )
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return self.store_name.lower()


