"""
Embedding service using OpenRouter API for semantic search.

Converts text to dense vectors using OpenRouter's embedding models.
Used for creating embeddings of products and user queries.
"""

import logging
from typing import List, Optional
import numpy as np
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for creating text embeddings using OpenRouter API.

    Uses text-embedding-3-small model via OpenRouter:
    - 1536 dimensions
    - API-based inference (no local model needed)
    - High quality semantic understanding
    - Suitable for product matching
    - Reduces Docker image size significantly
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding service with OpenRouter client.

        Args:
            model_name: Model to use (default: text-embedding-3-small)
        """
        self.model_name = model_name or settings.embedding_model
        self.api_key = settings.openrouter_api_key
        self.cache = {}
        self.base_url = "https://openrouter.ai/api/v1"

        logger.info(f"Initializing EmbeddingService with OpenRouter model: {self.model_name}")

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. Embeddings will fail.")
        else:
            logger.info(f"OpenRouter client initialized for embeddings: {self.model_name}")

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Embed a text string into a vector using OpenRouter API.

        Args:
            text: Text to embed

        Returns:
            List of floats (vector) or None if embedding fails
        """
        if not text:
            logger.warning("Empty text to embed")
            return None

        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not configured")
            return None

        try:
            # Check cache
            if text in self.cache:
                logger.debug(f"Cache hit for embedding: {text[:50]}...")
                return self.cache[text]

            # Call OpenRouter API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"input": text, "model": self.model_name}
                )
                response.raise_for_status()
                data = response.json()

            vector = data["data"][0]["embedding"]

            # Cache result
            self.cache[text] = vector

            logger.debug(f"Embedded text: {text[:50]}... -> {len(vector)}-dim vector")
            return vector

        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            return None

    async def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Embed multiple texts in batch using OpenRouter API.

        More efficient than embedding texts one-by-one.

        Args:
            texts: List of texts to embed

        Returns:
            List of vectors or None if embedding fails
        """
        if not texts:
            logger.warning("Empty texts list to embed")
            return None

        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not configured")
            return None

        try:
            # Separate cached and uncached texts
            cached = []
            uncached = []
            uncached_indices = []

            for i, text in enumerate(texts):
                if text in self.cache:
                    cached.append(self.cache[text])
                else:
                    uncached.append(text)
                    uncached_indices.append(i)

            # Embed uncached texts
            if uncached:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"input": uncached, "model": self.model_name}
                    )
                    response.raise_for_status()
                    data = response.json()

                uncached_vectors = [item["embedding"] for item in data["data"]]

                # Cache results
                for text, vector in zip(uncached, uncached_vectors):
                    self.cache[text] = vector
            else:
                uncached_vectors = []

            # Combine results in original order
            results = [None] * len(texts)
            cached_idx = 0
            uncached_idx = 0

            for i, text in enumerate(texts):
                if text in self.cache:
                    results[i] = self.cache[text]
                else:
                    results[i] = uncached_vectors[uncached_idx]
                    uncached_idx += 1

            logger.debug(f"Embedded {len(texts)} texts (cached: {len(cached)}, new: {len(uncached_vectors)})")
            return results

        except Exception as e:
            logger.error(f"Error embedding texts: {str(e)}")
            return None

    async def embed_documents(self, documents: List[str]) -> Optional[List[List[float]]]:
        """
        Embed multiple documents (same as embed_texts but semantic naming).

        Args:
            documents: List of documents to embed

        Returns:
            List of vectors
        """
        return await self.embed_texts(documents)

    async def similarity_search(
        self,
        query_vector: List[float],
        document_vectors: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar documents using cosine similarity.

        Args:
            query_vector: Query embedding
            document_vectors: List of document embeddings
            top_k: Number of results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        if not query_vector or not document_vectors:
            return []

        try:
            query = np.array(query_vector)

            similarities = []
            for i, doc_vector in enumerate(document_vectors):
                doc = np.array(doc_vector)

                # Cosine similarity (dot product for normalized vectors)
                similarity = float(np.dot(query, doc))
                similarities.append((i, similarity))

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Return top-k
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return []

    def get_embedding_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Number of dimensions in embeddings
        """
        return settings.embedding_dimension

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self.cache.clear()
        logger.debug("Cleared embedding cache")

    async def close(self) -> None:
        """Close service (cleanup)."""
        self.clear_cache()
        logger.debug("Closed EmbeddingService")

    def __repr__(self) -> str:
        return f"<EmbeddingService model={self.model_name}>"
