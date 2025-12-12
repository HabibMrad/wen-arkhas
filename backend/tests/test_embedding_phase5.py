"""
Unit tests for Phase 5 embedding and RAG functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np
from app.services.embedding import EmbeddingService
from app.services.pinecone_db import PineconeDB
from app.agents.rag import RAGAgent
from app.models.schemas import ProductModel, ParsedQuery, MatchedProduct


class TestEmbeddingService:
    """Tests for EmbeddingService"""

    def test_init(self):
        """Test EmbeddingService initialization"""
        with patch("app.services.embedding.SentenceTransformer"):
            service = EmbeddingService()
            assert service.cache == {}

    def test_init_custom_model(self):
        """Test initialization with custom model"""
        with patch("app.services.embedding.SentenceTransformer"):
            service = EmbeddingService(model_name="custom-model")
            assert service.model_name == "custom-model"

    @pytest.mark.asyncio
    async def test_embed_text_valid(self):
        """Test embedding valid text"""
        service = EmbeddingService()

        # Mock model
        mock_embeddings = np.array([[0.1, 0.2, 0.3]])
        service.model = Mock()
        service.model.encode = Mock(return_value=mock_embeddings)

        result = await service.embed_text("test text")

        assert result is not None
        assert len(result) == 3
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_text_empty(self):
        """Test embedding empty text"""
        service = EmbeddingService()

        result = await service.embed_text("")

        assert result is None

    @pytest.mark.asyncio
    async def test_embed_text_cache(self):
        """Test embedding cache"""
        service = EmbeddingService()

        # Mock model
        mock_embeddings = np.array([[0.1, 0.2, 0.3]])
        service.model = Mock()
        service.model.encode = Mock(return_value=mock_embeddings)

        # First embedding (cache miss)
        result1 = await service.embed_text("test")
        assert service.model.encode.call_count == 1

        # Second embedding (cache hit)
        result2 = await service.embed_text("test")
        assert service.model.encode.call_count == 1  # No new call
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_embed_texts_batch(self):
        """Test batch embedding"""
        service = EmbeddingService()

        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        service.model = Mock()
        service.model.encode = Mock(return_value=mock_embeddings)

        result = await service.embed_texts(["text1", "text2"])

        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_similarity_search(self):
        """Test similarity search"""
        service = EmbeddingService()

        query_vector = [0.1, 0.2, 0.3]
        doc_vectors = [
            [0.1, 0.2, 0.3],  # Identical - score 1.0
            [0.2, 0.3, 0.4],  # Similar
            [-0.1, -0.2, -0.3],  # Opposite - score -1.0
        ]

        results = await service.similarity_search(query_vector, doc_vectors, top_k=2)

        assert len(results) == 2
        assert results[0][0] == 0  # Most similar
        assert results[0][1] > results[1][1]  # Decreasing similarity

    def test_clear_cache(self):
        """Test clearing cache"""
        service = EmbeddingService()
        service.cache = {"test": [0.1, 0.2]}

        service.clear_cache()

        assert service.cache == {}

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing service"""
        service = EmbeddingService()
        service.cache = {"test": [0.1, 0.2]}

        await service.close()

        assert service.cache == {}


class TestPineconeDB:
    """Tests for PineconeDB"""

    def test_init(self):
        """Test PineconeDB initialization"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB(api_key="test-key", index_name="test-index")

            assert db.api_key == "test-key"
            assert db.index_name == "test-index"

    @pytest.mark.asyncio
    async def test_upsert_vectors_empty(self):
        """Test upserting empty vector list"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB()

            result = await db.upsert_vectors([])

            assert result is True

    @pytest.mark.asyncio
    async def test_upsert_vectors_valid(self):
        """Test upserting valid vectors"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB()
            db.index = Mock()
            db.index.upsert = Mock()

            vectors = [
                {
                    "id": "v1",
                    "values": [0.1, 0.2, 0.3],
                    "metadata": {"title": "Product 1"}
                },
                {
                    "id": "v2",
                    "values": [0.4, 0.5, 0.6],
                    "metadata": {"title": "Product 2"}
                }
            ]

            result = await db.upsert_vectors(vectors)

            assert result is True
            assert db.index.upsert.called

    @pytest.mark.asyncio
    async def test_search_valid(self):
        """Test searching vectors"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB()
            db.index = Mock()
            db.index.query = Mock(return_value={
                "matches": [
                    {"id": "v1", "score": 0.95, "metadata": {"title": "Product 1"}},
                    {"id": "v2", "score": 0.85, "metadata": {"title": "Product 2"}}
                ]
            })

            results = await db.search([0.1, 0.2, 0.3], top_k=10)

            assert len(results) == 2
            assert results[0]["id"] == "v1"
            assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_delete_by_id(self):
        """Test deleting vectors by ID"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB()
            db.index = Mock()
            db.index.delete = Mock()

            result = await db.delete_by_id(["v1", "v2"])

            assert result is True
            assert db.index.delete.called

    @pytest.mark.asyncio
    async def test_get_index_stats(self):
        """Test getting index statistics"""
        with patch("app.services.pinecone_db.Pinecone"):
            db = PineconeDB()
            db.index = Mock()
            db.index.describe_index_stats = Mock(return_value={
                "total_vector_count": 1000,
                "dimension": 384,
                "namespaces": {}
            })

            stats = await db.get_index_stats()

            assert stats is not None
            assert stats["total_vectors"] == 1000
            assert stats["dimension"] == 384


class TestRAGAgent:
    """Tests for RAGAgent"""

    def test_init(self):
        """Test RAGAgent initialization"""
        with patch("app.services.embedding.SentenceTransformer"):
            with patch("app.services.pinecone_db.Pinecone"):
                agent = RAGAgent()

                assert agent.embedding_service is not None
                assert agent.pinecone_db is not None

    def test_create_product_text(self):
        """Test creating product text for embedding"""
        with patch("app.services.embedding.SentenceTransformer"):
            with patch("app.services.pinecone_db.Pinecone"):
                agent = RAGAgent()

                product = ProductModel(
                    product_id="p1",
                    store_id="s1",
                    title="Adidas Samba",
                    price=99.99,
                    url="https://example.com/p1"
                )

                text = agent._create_product_text(product)

                assert "Adidas Samba" in text

    def test_build_search_query(self):
        """Test building search query"""
        with patch("app.services.embedding.SentenceTransformer"):
            with patch("app.services.pinecone_db.Pinecone"):
                agent = RAGAgent()

                parsed = ParsedQuery(
                    brand="Adidas",
                    model="Samba",
                    category="shoes",
                    size="42",
                    gender="men",
                    color="black",
                    original_query="adidas samba"
                )

                query = agent._build_search_query(parsed)

                assert "Adidas" in query
                assert "Samba" in query
                assert "shoes" in query

    @pytest.mark.asyncio
    async def test_execute_no_products(self):
        """Test execute with no products"""
        with patch("app.services.embedding.SentenceTransformer"):
            with patch("app.services.pinecone_db.Pinecone"):
                agent = RAGAgent()

                state = {
                    "raw_products": [],
                    "parsed_query": ParsedQuery(
                        brand="Nike",
                        original_query="nike",
                        model=None,
                        category=None,
                        size=None,
                        gender=None,
                        color=None
                    ),
                    "matched_products": [],
                    "errors": [],
                    "execution_time_ms": {}
                }

                result = await agent.execute(state)

                assert result["matched_products"] == []

    @pytest.mark.asyncio
    async def test_execute_no_parsed_query(self):
        """Test execute without parsed query"""
        with patch("app.services.embedding.SentenceTransformer"):
            with patch("app.services.pinecone_db.Pinecone"):
                agent = RAGAgent()

                product = ProductModel(
                    product_id="p1",
                    store_id="s1",
                    title="Product",
                    price=99.99,
                    url="https://example.com"
                )

                state = {
                    "raw_products": [product],
                    "parsed_query": None,
                    "matched_products": [],
                    "errors": [],
                    "execution_time_ms": {}
                }

                result = await agent.execute(state)

                assert len(result["errors"]) > 0


class TestRAGIntegration:
    """Integration tests for RAG system"""

    def test_product_model_to_matched_product(self):
        """Test converting ProductModel to MatchedProduct"""
        product = ProductModel(
            product_id="p1",
            store_id="s1",
            title="Adidas Samba",
            price=99.99,
            currency="USD",
            rating=4.5,
            reviews_count=50,
            availability=True,
            url="https://example.com/p1"
        )

        matched = MatchedProduct(
            product_id=product.product_id,
            store_id=product.store_id,
            title=product.title,
            price=product.price,
            currency=product.currency,
            rating=product.rating,
            reviews_count=product.reviews_count,
            availability=product.availability,
            url=product.url,
            similarity_score=0.95,
            store_name="Nike Store",
            distance_km=2.5
        )

        assert matched.product_id == "p1"
        assert matched.similarity_score == 0.95
        assert matched.store_name == "Nike Store"

    def test_embedding_dimension(self):
        """Test embedding dimension"""
        with patch("app.services.embedding.SentenceTransformer"):
            service = EmbeddingService()

            dim = service.get_embedding_dimension()

            assert dim == 384  # all-MiniLM-L6-v2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
