"""
Pinecone vector database service for semantic search.

Handles:
- Index creation and management
- Vector upsertion (insert/update)
- Similarity search
- Metadata filtering
"""

import logging
from typing import Dict, List, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone
except ImportError:
    logger.warning("pinecone-client not installed. Install with: pip install pinecone-client")
    Pinecone = None


class PineconeDB:
    """
    Service for managing Pinecone vector database.

    Features:
    - Automatic index creation
    - Batch upsert of vectors
    - Similarity search with metadata
    - Filtering by metadata
    - Index statistics
    """

    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None):
        """
        Initialize Pinecone service.

        Args:
            api_key: Pinecone API key (default from settings)
            index_name: Index name (default from settings)
        """
        if Pinecone is None:
            logger.error("pinecone-client not installed")
            self.client = None
            self.index = None
            return

        self.api_key = api_key or settings.pinecone_api_key
        self.index_name = index_name or settings.pinecone_index_name
        self.client = None
        self.index = None

        logger.info(f"Initializing Pinecone service - Index: {self.index_name}")

        try:
            # Initialize Pinecone client
            self.client = Pinecone(api_key=self.api_key)
            logger.info("Pinecone client initialized")

            # Get or create index
            self._ensure_index_exists()

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            self.client = None
            self.index = None

    def _ensure_index_exists(self) -> bool:
        """
        Ensure index exists in Pinecone, create if not.

        Returns:
            True if index exists or was created
        """
        if self.client is None:
            logger.error("Pinecone client not initialized")
            return False

        try:
            # Get existing indexes
            indexes = self.client.list_indexes()
            existing_index_names = [idx.name for idx in indexes]

            if self.index_name in existing_index_names:
                logger.info(f"Index exists: {self.index_name}")
                self.index = self.client.Index(self.index_name)
                return True

            # Create new index
            logger.info(f"Creating index: {self.index_name}")

            self.client.create_index(
                name=self.index_name,
                dimension=settings.embedding_dimension,  # 384 for all-MiniLM-L6-v2
                metric="cosine",  # Cosine similarity
                spec={
                    "serverless": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    }
                }
            )

            self.index = self.client.Index(self.index_name)
            logger.info(f"Created index: {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Error ensuring index exists: {str(e)}")
            return False

    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]]
    ) -> bool:
        """
        Upsert vectors to Pinecone index.

        Args:
            vectors: List of vector dicts with 'id', 'values', 'metadata'

        Returns:
            True if successful
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return False

        if not vectors:
            logger.warning("No vectors to upsert")
            return True

        try:
            logger.debug(f"Upserting {len(vectors)} vectors")

            # Convert to Pinecone format: (id, values, metadata)
            formatted_vectors = [
                (
                    v["id"],
                    v["values"],
                    v.get("metadata", {})
                )
                for v in vectors
            ]

            # Upsert in batches (Pinecone recommends ~100 per batch)
            batch_size = 100
            for i in range(0, len(formatted_vectors), batch_size):
                batch = formatted_vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                logger.debug(f"Upserted batch {i // batch_size + 1}")

            logger.info(f"Successfully upserted {len(vectors)} vectors")
            return True

        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            return False

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 20,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Pinecone.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of results with 'id', 'score', 'metadata'
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return []

        try:
            logger.debug(f"Searching for top {top_k} similar vectors")

            # Query index
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )

            # Format results
            matches = []
            for match in results.get("matches", []):
                matches.append({
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "metadata": match.get("metadata", {})
                })

            logger.debug(f"Found {len(matches)} similar vectors")
            return matches

        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            return []

    async def delete_by_id(self, ids: List[str]) -> bool:
        """
        Delete vectors by ID.

        Args:
            ids: List of vector IDs to delete

        Returns:
            True if successful
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return False

        try:
            self.index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors")
            return True
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            return False

    async def delete_all(self) -> bool:
        """
        Delete all vectors from index.

        Use with caution - this is irreversible!

        Returns:
            True if successful
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return False

        try:
            logger.warning("Deleting all vectors from index")
            self.index.delete(delete_all=True)
            logger.info("Deleted all vectors")
            return True
        except Exception as e:
            logger.error(f"Error deleting all vectors: {str(e)}")
            return False

    async def get_index_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get index statistics.

        Returns:
            Dictionary with index stats or None
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return None

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count"),
                "dimension": stats.get("dimension"),
                "namespaces": stats.get("namespaces", {})
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return None

    async def close(self) -> None:
        """Close Pinecone connection."""
        logger.debug("Closed Pinecone service")

    def __repr__(self) -> str:
        return f"<PineconeDB index={self.index_name}>"
