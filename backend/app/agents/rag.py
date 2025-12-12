"""
LangGraph Agent Node: Semantic Matching with RAG (Retrieval-Augmented Generation).

Uses embeddings and Pinecone vector database to find the most relevant products.

Responsibilities:
- Embed products using sentence-transformers
- Store embeddings in Pinecone
- Perform semantic search
- Match products to user query
- Return top-K most relevant products

Input: SearchState with 'raw_products' field
Output: SearchState with 'matched_products' field populated
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from app.services.embedding import EmbeddingService
from app.services.pinecone_db import PineconeDB
from app.models.schemas import SearchState, ProductModel, MatchedProduct
from app.config import settings

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    LangGraph Agent Node: Performs semantic matching using embeddings and vector DB.

    Uses:
    - sentence-transformers for product embeddings
    - Pinecone for vector storage and similarity search
    - Cosine similarity for matching

    Architecture:
    1. Embed products with sentence-transformers (384-dim vectors)
    2. Store in Pinecone with metadata
    3. Embed user query
    4. Search Pinecone for top-K similar products
    5. Return matched products with similarity scores
    """

    def __init__(self):
        """Initialize RAGAgent with embedding and vector DB services."""
        self.embedding_service = EmbeddingService()
        self.pinecone_db = PineconeDB()
        logger.info("RAGAgent initialized")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match products to user query using semantic search.

        Args:
            state: SearchState with 'raw_products' and 'parsed_query'

        Returns:
            Updated state with 'matched_products' field
        """
        start_time = time.time()
        logger.info("RAGAgent starting")

        try:
            # Get raw products
            raw_products = state.get("raw_products", [])
            if not raw_products:
                logger.warning("No raw products to match")
                state["matched_products"] = []
                state["execution_time_ms"]["match_products"] = int(
                    (time.time() - start_time) * 1000
                )
                return state

            # Get parsed query for context
            parsed_query = state.get("parsed_query")
            if not parsed_query:
                error_msg = "No parsed query available"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Convert raw products to ProductModel if needed
            products = []
            for p in raw_products:
                if isinstance(p, dict):
                    products.append(ProductModel(**p))
                else:
                    products.append(p)

            logger.info(f"Matching {len(products)} products")

            # Index products in Pinecone (if not already indexed)
            await self._index_products(products)

            # Build search query
            search_query = self._build_search_query(parsed_query)
            logger.debug(f"Search query: {search_query}")

            # Embed query
            query_embedding = await self.embedding_service.embed_text(search_query)
            if query_embedding is None:
                error_msg = "Failed to embed query"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Search Pinecone
            matched_products = await self._search_and_match(
                query_embedding,
                products,
                top_k=20
            )

            logger.info(f"Matched {len(matched_products)} products")
            state["matched_products"] = matched_products

            # Track execution time
            state["execution_time_ms"]["match_products"] = int(
                (time.time() - start_time) * 1000
            )

            logger.info(f"RAGAgent completed in {state['execution_time_ms']['match_products']}ms")

            return state

        except Exception as e:
            error_msg = f"RAGAgent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            return state

    async def _index_products(self, products: List[ProductModel]) -> bool:
        """
        Index products in Pinecone vector database.

        Args:
            products: List of products to index

        Returns:
            True if successful
        """
        try:
            logger.info(f"Indexing {len(products)} products in Pinecone")

            # Embed products in batches
            vectors = []
            for product in products:
                # Create product text for embedding
                text = self._create_product_text(product)

                # Embed text
                embedding = await self.embedding_service.embed_text(text)
                if embedding is None:
                    logger.warning(f"Failed to embed product: {product.title}")
                    continue

                # Create vector with metadata
                vector = {
                    "id": product.product_id,
                    "values": embedding,
                    "metadata": {
                        "product_id": product.product_id,
                        "store_id": product.store_id,
                        "title": product.title,
                        "price": float(product.price),
                        "rating": product.rating or 0.0,
                        "url": product.url or "",
                    }
                }
                vectors.append(vector)

            if not vectors:
                logger.warning("No vectors to index")
                return False

            # Upsert to Pinecone
            success = await self.pinecone_db.upsert_vectors(vectors)

            if success:
                logger.info(f"Successfully indexed {len(vectors)} products")
            else:
                logger.error("Failed to upsert vectors to Pinecone")

            return success

        except Exception as e:
            logger.error(f"Error indexing products: {str(e)}")
            return False

    async def _search_and_match(
        self,
        query_embedding: List[float],
        products: List[ProductModel],
        top_k: int = 20
    ) -> List[MatchedProduct]:
        """
        Search Pinecone and match results to products.

        Args:
            query_embedding: Embedded query vector
            products: Original product list
            top_k: Number of results to return

        Returns:
            List of MatchedProduct objects
        """
        try:
            # Search Pinecone
            results = await self.pinecone_db.search(query_embedding, top_k=top_k)

            if not results:
                logger.warning("No search results from Pinecone")
                return []

            # Create product map for quick lookup
            product_map = {p.product_id: p for p in products}

            # Build matched products with similarity scores
            matched = []
            for i, result in enumerate(results):
                product_id = result.get("id")
                similarity_score = result.get("score", 0.0)
                metadata = result.get("metadata", {})

                # Find original product
                original_product = product_map.get(product_id)
                if not original_product:
                    logger.debug(f"Product not found: {product_id}")
                    continue

                # Create matched product
                matched_product = MatchedProduct(
                    product_id=original_product.product_id,
                    store_id=original_product.store_id,
                    title=original_product.title,
                    price=original_product.price,
                    currency=original_product.currency,
                    rating=original_product.rating,
                    reviews_count=original_product.reviews_count,
                    availability=original_product.availability,
                    url=original_product.url,
                    image_url=original_product.image_url,
                    specs=original_product.specs,
                    description=original_product.description,
                    similarity_score=similarity_score,
                    store_name=metadata.get("store_name", "Unknown"),
                    distance_km=metadata.get("distance_km", 0.0),
                )

                matched.append(matched_product)

            logger.debug(f"Created {len(matched)} matched products")
            return matched

        except Exception as e:
            logger.error(f"Error searching and matching: {str(e)}")
            return []

    def _create_product_text(self, product: ProductModel) -> str:
        """
        Create text representation of product for embedding.

        Combines all relevant fields for better semantic matching.

        Args:
            product: ProductModel to embed

        Returns:
            Text representation for embedding
        """
        parts = []

        if product.title:
            parts.append(product.title)

        if product.description:
            parts.append(product.description)

        if product.specs:
            for key, value in product.specs.items():
                parts.append(f"{key}: {value}")

        return " ".join(parts) if parts else product.title

    def _build_search_query(self, parsed_query) -> str:
        """
        Build search query from parsed query for embedding.

        Args:
            parsed_query: ParsedQuery object

        Returns:
            Search query string
        """
        terms = []

        if parsed_query.brand:
            terms.append(parsed_query.brand)
        if parsed_query.model:
            terms.append(parsed_query.model)
        if parsed_query.category:
            terms.append(parsed_query.category)
        if parsed_query.gender:
            terms.append(parsed_query.gender)
        if parsed_query.color:
            terms.append(parsed_query.color)
        if parsed_query.size:
            terms.append(f"size {parsed_query.size}")

        return " ".join(terms) if terms else parsed_query.original_query

    async def close(self) -> None:
        """Close connections."""
        await self.embedding_service.close()
        await self.pinecone_db.close()


# Define the async node function for LangGraph
async def match_products_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for product matching.

    Args:
        state: Current workflow state

    Returns:
        Updated state with matched_products
    """
    agent = RAGAgent()
    try:
        return await agent.execute(state)
    finally:
        await agent.close()
