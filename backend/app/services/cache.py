import json
import logging
from typing import Any, Optional, Dict, List
import redis
import hashlib
from app.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based cache manager with support for different TTLs
    for different data types.
    """

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis connection.

        Args:
            redis_url: Redis connection URL (default from config)
        """
        self.redis_url = redis_url or settings.redis_url
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.client = None

    def _is_connected(self) -> bool:
        """Check if Redis is connected"""
        if self.client is None:
            logger.warning("Redis client is not initialized")
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    async def get_stores(self, key: str) -> Optional[List[Dict]]:
        """
        Get cached stores.

        Args:
            key: Cache key (format: "stores:{lat}:{lng}:{category}")

        Returns:
            List of store dicts or None if not cached/expired
        """
        if not self._is_connected():
            return None

        try:
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving stores from cache: {str(e)}")
            return None

    async def set_stores(
        self,
        key: str,
        stores: List[Dict],
        ttl_hours: int = None
    ) -> bool:
        """
        Cache stores with 24h default TTL.

        Args:
            key: Cache key
            stores: List of store dictionaries
            ttl_hours: Time to live in hours (default: 24h)

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        if ttl_hours is None:
            ttl_hours = settings.cache_ttl_stores_hours

        try:
            ttl_seconds = ttl_hours * 3600
            self.client.setex(
                key,
                ttl_seconds,
                json.dumps(stores, default=str)
            )
            logger.debug(f"Cached stores: {key} (TTL: {ttl_hours}h)")
            return True
        except Exception as e:
            logger.error(f"Error caching stores: {str(e)}")
            return False

    async def get_products(self, key: str) -> Optional[List[Dict]]:
        """
        Get cached products.

        Args:
            key: Cache key (format: "products:{store_id}:{query_hash}")

        Returns:
            List of product dicts or None
        """
        if not self._is_connected():
            return None

        try:
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving products from cache: {str(e)}")
            return None

    async def set_products(
        self,
        key: str,
        products: List[Dict],
        ttl_hours: int = None
    ) -> bool:
        """
        Cache products with 6h default TTL.

        Args:
            key: Cache key
            products: List of product dictionaries
            ttl_hours: Time to live in hours (default: 6h)

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        if ttl_hours is None:
            ttl_hours = settings.cache_ttl_products_hours

        try:
            ttl_seconds = ttl_hours * 3600
            self.client.setex(
                key,
                ttl_seconds,
                json.dumps(products, default=str)
            )
            logger.debug(f"Cached products: {key} (TTL: {ttl_hours}h)")
            return True
        except Exception as e:
            logger.error(f"Error caching products: {str(e)}")
            return False

    async def get_search(self, key: str) -> Optional[Dict]:
        """
        Get cached search results.

        Args:
            key: Cache key (format: "{lat}:{lng}:{query}")

        Returns:
            Search result dict or None
        """
        if not self._is_connected():
            return None

        try:
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving search from cache: {str(e)}")
            return None

    async def set_search(
        self,
        key: str,
        result: Dict,
        ttl_hours: int = None
    ) -> bool:
        """
        Cache full search results with 1h default TTL.

        Args:
            key: Cache key
            result: Search result dictionary
            ttl_hours: Time to live in hours (default: 1h)

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        if ttl_hours is None:
            ttl_hours = settings.cache_ttl_search_hours

        try:
            ttl_seconds = ttl_hours * 3600
            self.client.setex(
                key,
                ttl_seconds,
                json.dumps(result, default=str)
            )
            logger.debug(f"Cached search: {key} (TTL: {ttl_hours}h)")
            return True
        except Exception as e:
            logger.error(f"Error caching search: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        try:
            self.client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache: {str(e)}")
            return False

    async def clear_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "stores:*", "products:123:*")

        Returns:
            Number of keys deleted
        """
        if not self._is_connected():
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache by pattern: {str(e)}")
            return 0

    async def flush_all(self) -> bool:
        """
        Clear all cache (use with caution).

        Returns:
            True if successful
        """
        if not self._is_connected():
            return False

        try:
            self.client.flushdb()
            logger.warning("Cache flushed completely")
            return True
        except Exception as e:
            logger.error(f"Error flushing cache: {str(e)}")
            return False

    @staticmethod
    def generate_key(*parts: str) -> str:
        """
        Generate a cache key from parts.

        Args:
            *parts: Key components

        Returns:
            Cache key
        """
        return ":".join(str(p) for p in parts)

    @staticmethod
    def generate_hash(text: str) -> str:
        """
        Generate a hash for a string (useful for query hashing).

        Args:
            text: Text to hash

        Returns:
            MD5 hash
        """
        return hashlib.md5(text.encode()).hexdigest()

    async def get_stats(self) -> Optional[Dict]:
        """
        Get Redis cache statistics.

        Returns:
            Dictionary with cache stats or None
        """
        if not self._is_connected():
            return None

        try:
            info = self.client.info()
            return {
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "uptime_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return None
