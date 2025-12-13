import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_places_api_key: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")

    # Pinecone Configuration
    pinecone_environment: str = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "wen-arkhas-products")
    pinecone_host: Optional[str] = os.getenv("PINECONE_HOST", None)

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # App Configuration
    app_name: str = "Wen-Arkhas"
    app_version: str = "0.1.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # LangGraph Configuration
    default_model: str = "anthropic/claude-sonnet-4-20250514"
    fallback_model: str = "openai/gpt-4o"

    # Service Configuration
    max_stores_per_search: int = 10
    store_search_radius_km: int = 10
    min_store_rating: float = 3.5

    # Cache TTL (Time To Live)
    cache_ttl_stores_hours: int = 24
    cache_ttl_products_hours: int = 6
    cache_ttl_search_hours: int = 1

    # Scraper Configuration
    scraper_rate_limit_per_second: float = 1.0
    scraper_timeout_seconds: int = 30
    scraper_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Location Validation (Lebanon bounds)
    min_latitude: float = 33.0
    max_latitude: float = 34.7
    min_longitude: float = 35.1
    max_longitude: float = 36.6

    # Embeddings Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # API Configuration
    api_prefix: str = "/api"
    cors_origins: list = ["http://localhost:3000", "https://wen-arkhas.app"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Singleton instance
settings = Settings()
