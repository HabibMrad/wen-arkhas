"""
Playwright scraper for JavaScript-heavy sites.
Uses Playwright to render JavaScript and interact with pages.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScraperError, ScraperTimeoutError
from app.models.schemas import ProductModel
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    logger.warning("Playwright not installed. Install with: pip install playwright")
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None


class PlaywrightScraper(BaseScraper):
    """
    Scraper for JavaScript-heavy sites using Playwright.

    Capabilities:
    - Render JavaScript
    - Wait for dynamic content
    - Handle infinite scroll
    - Click buttons, fill forms
    - Take screenshots for debugging

    Good for:
    - React/Vue/Angular sites
    - Sites with lazy loading
    - Sites with modal popups
    - Sites with infinite scroll
    """

    def __init__(self, store_name: str, store_url: str):
        """
        Initialize Playwright scraper.

        Args:
            store_name: Name of the store
            store_url: Base URL of the store
        """
        super().__init__(store_name, store_url, rate_limit_delay=2.0)
        self.browser = None
        self.context = None
        self.playwright = None
        logger.info(f"Initialized Playwright scraper for {store_name}")

    async def _get_browser(self) -> Optional[Browser]:
        """
        Get or create browser instance.

        Returns:
            Browser instance or None if Playwright not available
        """
        if self.browser is not None:
            return self.browser

        if async_playwright is None:
            logger.error("Playwright not installed")
            return None

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True  # Run in headless mode (no GUI)
            )
            logger.info(f"Launched browser for {self.store_name}")
            return self.browser
        except Exception as e:
            logger.error(f"Failed to launch browser: {str(e)}")
            return None

    async def _get_context(self) -> Optional[BrowserContext]:
        """
        Get or create browser context.

        Returns:
            BrowserContext or None
        """
        if self.context is not None:
            return self.context

        browser = await self._get_browser()
        if browser is None:
            return None

        try:
            self.context = await browser.new_context(
                user_agent=settings.scraper_user_agent,
                viewport={"width": 1280, "height": 720},
            )
            logger.debug(f"Created browser context for {self.store_name}")
            return self.context
        except Exception as e:
            logger.error(f"Failed to create context: {str(e)}")
            return None

    async def scrape_search(self, query: str, **kwargs) -> List[ProductModel]:
        """
        Scrape products from JavaScript-heavy site.

        Args:
            query: Search query
            **kwargs: Additional parameters:
                - search_url: Full URL for search
                - wait_selector: CSS selector to wait for (default: product selector)
                - scroll_count: Number of scrolls for infinite scroll (default: 3)

        Returns:
            List of ProductModel objects
        """
        try:
            await self._respect_rate_limit()

            context = await self._get_context()
            if context is None:
                raise ScraperError(f"Could not create browser context for {self.store_name}")

            # Create page
            page = await context.new_page()

            try:
                # Build search URL
                search_url = kwargs.get("search_url")
                if not search_url:
                    search_url = self._build_search_url(query)

                logger.info(f"Scraping {self.store_name}: {query}")
                logger.debug(f"Search URL: {search_url}")

                # Navigate to page
                await page.goto(search_url, wait_until="networkidle", timeout=settings.scraper_timeout_seconds * 1000)

                # Handle dynamic content
                wait_selector = kwargs.get("wait_selector", "div.product")
                try:
                    await page.wait_for_selector(wait_selector, timeout=5000)
                except Exception:
                    logger.warning(f"Wait selector not found: {wait_selector}")

                # Handle infinite scroll
                scroll_count = kwargs.get("scroll_count", 3)
                for i in range(scroll_count):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(0.5)

                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # Extract products
                products = await self._extract_products_from_html(soup, query)

                logger.info(f"Extracted {len(products)} products from {self.store_name}")
                return products

            finally:
                await page.close()

        except asyncio.TimeoutError as e:
            error_msg = f"Timeout scraping {self.store_name}: {str(e)}"
            logger.error(error_msg)
            raise ScraperTimeoutError(error_msg)
        except Exception as e:
            error_msg = f"Error scraping {self.store_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ScraperError(error_msg)

    async def _extract_products_from_html(
        self,
        soup: BeautifulSoup,
        query: str
    ) -> List[ProductModel]:
        """
        Extract products from rendered HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            query: Original search query

        Returns:
            List of ProductModel objects
        """
        products = []

        # Find product elements
        product_selectors = [
            "div.product",
            "div.product-item",
            "article.product-card",
            "li.product",
        ]

        for selector in product_selectors:
            product_elements = soup.select(selector)
            if product_elements:
                logger.debug(f"Found {len(product_elements)} products with selector: {selector}")
                break
        else:
            logger.warning(f"Could not find product elements in {self.store_name}")
            return products

        for element in product_elements:
            try:
                product = self._parse_product(self._element_to_dict(element))
                if product and self._validate_product(product):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Failed to parse product: {str(e)}")
                continue

        return products

    def _element_to_dict(self, element) -> Dict[str, Any]:
        """
        Convert BeautifulSoup element to dictionary.

        Args:
            element: BeautifulSoup element

        Returns:
            Dictionary representation
        """
        return {
            "title": element.select_one("h2, h3, .title, .name"),
            "price": element.select_one(".price, .product-price"),
            "url": element.select_one("a"),
            "image": element.select_one("img"),
            "rating": element.select_one(".rating, .stars"),
            "raw_html": element,
        }

    def _parse_product(self, data: Dict[str, Any]) -> Optional[ProductModel]:
        """
        Parse product data from element dictionary.

        Override in subclasses for store-specific parsing.

        Args:
            data: Dictionary with product data

        Returns:
            ProductModel or None
        """
        try:
            title_elem = data.get("title")
            price_elem = data.get("price")
            url_elem = data.get("url")

            title = title_elem.get_text(strip=True) if title_elem else None
            price_text = price_elem.get_text(strip=True) if price_elem else None
            url = url_elem.get("href") if url_elem else None

            if not title or not price_text:
                return None

            # Parse price
            price = self._parse_price(price_text)
            if price is None:
                return None

            # Generate product ID
            product_id = f"{self.get_store_id()}_{hash(title) % 1000000}"

            # Build full URL if relative
            if url and not url.startswith("http"):
                url = self.store_url + (url if url.startswith("/") else "/" + url)

            product = self._build_product(
                product_id=product_id,
                store_id=self.get_store_id(),
                title=title,
                price=price,
                url=url,
            )

            return product

        except Exception as e:
            logger.debug(f"Error parsing product: {str(e)}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price from text.

        Args:
            price_text: Price text

        Returns:
            Float price or None
        """
        import re
        price_text = price_text.replace("USD", "").replace("$", "").strip()
        match = re.search(r"(\d+\.?\d*)", price_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _build_search_url(self, query: str) -> str:
        """
        Build search URL.

        Override in subclasses for store-specific patterns.

        Args:
            query: Search query

        Returns:
            Full search URL
        """
        query_param = query.replace(" ", "+")
        return f"{self.store_url}/search?q={query_param}"

    async def close(self) -> None:
        """Close browser and context."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info(f"Closed browser for {self.store_name}")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

    async def aclose(self) -> None:
        """Async close."""
        await self.close()


def create_playwright_scraper(store_name: str, store_url: str) -> PlaywrightScraper:
    """
    Create a Playwright scraper instance.

    Args:
        store_name: Name of the store
        store_url: Base URL of the store

    Returns:
        PlaywrightScraper instance
    """
    return PlaywrightScraper(store_name, store_url)
