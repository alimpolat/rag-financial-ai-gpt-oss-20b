"""
Comprehensive unit tests for RAG service.
Tests cover initialization, document indexing, querying, and error handling.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import chromadb
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.response import Response

from services.rag_service import RAGService
from core.exceptions import (
    RAGPipelineError,
    VectorStoreError,
    OllamaConnectionError,
    ServiceInitializationError
)


class TestRAGService:
    """Test suite for RAG service."""
    
    @pytest.fixture
    async def rag_service(self):
        """Create RAG service instance for testing."""
        service = RAGService()
        return service
    
    @pytest.fixture
    def mock_ollama(self):
        """Mock Ollama LLM."""
        with patch('services.rag_service.Ollama') as mock:
            mock_instance = MagicMock()
            mock_instance.complete = AsyncMock(return_value="Test response")
            mock.return_value = mock_instance
            yield mock
    
    @pytest.fixture
    def mock_chroma_client(self):
        """Mock ChromaDB client."""
        with patch('services.rag_service.chromadb.PersistentClient') as mock:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock ChromaVectorStore."""
        with patch('services.rag_service.ChromaVectorStore') as mock:
            mock_store = MagicMock()
            mock.return_value = mock_store
            yield mock_store
    
    @pytest.fixture
    def mock_vector_index(self):
        """Mock VectorStoreIndex."""
        with patch('services.rag_service.VectorStoreIndex') as mock:
            mock_index = MagicMock()
            mock.from_vector_store.return_value = mock_index
            mock.return_value = mock_index
            yield mock_index
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing."""
        return [
            Document(text="Financial report Q1 2024 shows revenue growth of 15%", doc_id="doc1"),
            Document(text="Market analysis indicates strong performance in tech sector", doc_id="doc2"),
            Document(text="Risk assessment for portfolio diversification strategy", doc_id="doc3")
        ]
    
    @pytest.fixture
    def sample_nodes(self):
        """Sample nodes for testing retrieval."""
        return [
            NodeWithScore(
                node=TextNode(
                    text="Revenue increased by 15% in Q1 2024",
                    metadata={"source": "report_q1_2024.pdf", "page": 5}
                ),
                score=0.92
            ),
            NodeWithScore(
                node=TextNode(
                    text="Strong growth in technology investments",
                    metadata={"source": "market_analysis.pdf", "page": 12}
                ),
                score=0.85
            )
        ]
    
    @pytest.mark.asyncio
    async def test_initialization_success(
        self, rag_service, mock_ollama, mock_chroma_client, 
        mock_vector_store, mock_vector_index
    ):
        """Test successful RAG service initialization."""
        await rag_service.initialize()
        
        assert rag_service.vector_index is not None
        assert rag_service.query_engine is not None
        assert rag_service.chroma_client is not None
        assert rag_service.vector_store is not None
        
        mock_ollama.assert_called_once()
        mock_chroma_client.assert_called_once()
        mock_vector_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_ollama_connection_error(self, rag_service):
        """Test initialization failure when Ollama is not available."""
        with patch('services.rag_service.Ollama') as mock_ollama:
            mock_ollama.side_effect = Exception("Connection refused")
            
            with pytest.raises(ServiceInitializationError) as exc_info:
                await rag_service.initialize()
            
            assert "Failed to initialize Ollama" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialization_chroma_error(self, rag_service, mock_ollama):
        """Test initialization failure when ChromaDB fails."""
        with patch('services.rag_service.chromadb.PersistentClient') as mock_chroma:
            mock_chroma.side_effect = Exception("ChromaDB connection failed")
            
            with pytest.raises(ServiceInitializationError) as exc_info:
                await rag_service.initialize()
            
            assert "Failed to initialize ChromaDB" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_add_documents_success(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index, sample_documents
    ):
        """Test successful document addition to index."""
        await rag_service.initialize()
        
        mock_index = rag_service.vector_index
        mock_index.insert_nodes = AsyncMock()
        
        result = await rag_service.add_documents(sample_documents)
        
        assert result["status"] == "success"
        assert result["documents_added"] == len(sample_documents)
        assert "processing_time" in result
        mock_index.insert_nodes.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_documents_empty_list(self, rag_service, mock_ollama, 
                                           mock_chroma_client, mock_vector_store, 
                                           mock_vector_index):
        """Test adding empty document list."""
        await rag_service.initialize()
        
        result = await rag_service.add_documents([])
        
        assert result["status"] == "success"
        assert result["documents_added"] == 0
    
    @pytest.mark.asyncio
    async def test_add_documents_not_initialized(self, rag_service):
        """Test adding documents when service not initialized."""
        with pytest.raises(ServiceInitializationError) as exc_info:
            await rag_service.add_documents([Document(text="test")])
        
        assert "RAG service not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_success(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index, sample_nodes
    ):
        """Test successful query execution."""
        await rag_service.initialize()
        
        # Mock query engine
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "Based on the financial reports, revenue grew by 15%"
        mock_response.source_nodes = sample_nodes
        mock_query_engine.query = AsyncMock(return_value=mock_response)
        rag_service.query_engine = mock_query_engine
        
        result = await rag_service.query("What was the revenue growth?")
        
        assert result["response"] == mock_response.response
        assert len(result["sources"]) == 2
        assert result["confidence"] > 0.8
        assert "processing_time" in result
        mock_query_engine.query.assert_called_once_with("What was the revenue growth?")
    
    @pytest.mark.asyncio
    async def test_query_with_filters(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index, sample_nodes
    ):
        """Test query with metadata filters."""
        await rag_service.initialize()
        
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "Filtered response"
        mock_response.source_nodes = [sample_nodes[0]]
        mock_query_engine.query = AsyncMock(return_value=mock_response)
        rag_service.query_engine = mock_query_engine
        
        filters = {"source": "report_q1_2024.pdf"}
        result = await rag_service.query("Revenue data", filters=filters)
        
        assert result["response"] == "Filtered response"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["metadata"]["source"] == "report_q1_2024.pdf"
    
    @pytest.mark.asyncio
    async def test_query_no_results(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test query with no matching results."""
        await rag_service.initialize()
        
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "No relevant information found."
        mock_response.source_nodes = []
        mock_query_engine.query = AsyncMock(return_value=mock_response)
        rag_service.query_engine = mock_query_engine
        
        result = await rag_service.query("Completely unrelated query")
        
        assert result["response"] == "No relevant information found."
        assert len(result["sources"]) == 0
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_query_ollama_timeout(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test query timeout handling."""
        await rag_service.initialize()
        
        mock_query_engine = MagicMock()
        mock_query_engine.query = AsyncMock(
            side_effect=TimeoutError("Ollama request timeout")
        )
        rag_service.query_engine = mock_query_engine
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            await rag_service.query("Test query")
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_query_not_initialized(self, rag_service):
        """Test querying when service not initialized."""
        with pytest.raises(ServiceInitializationError) as exc_info:
            await rag_service.query("Test query")
        
        assert "RAG service not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test successful document deletion."""
        await rag_service.initialize()
        
        mock_collection = MagicMock()
        mock_collection.delete = MagicMock()
        rag_service.chroma_client.get_or_create_collection.return_value = mock_collection
        
        result = await rag_service.delete_document("doc123")
        
        assert result["status"] == "success"
        assert result["document_id"] == "doc123"
        mock_collection.delete.assert_called_once_with(ids=["doc123"])
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test deleting non-existent document."""
        await rag_service.initialize()
        
        mock_collection = MagicMock()
        mock_collection.delete = MagicMock(side_effect=Exception("Document not found"))
        rag_service.chroma_client.get_or_create_collection.return_value = mock_collection
        
        with pytest.raises(VectorStoreError) as exc_info:
            await rag_service.delete_document("non_existent")
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_statistics(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test getting RAG service statistics."""
        await rag_service.initialize()
        
        mock_collection = MagicMock()
        mock_collection.count = MagicMock(return_value=150)
        rag_service.chroma_client.get_or_create_collection.return_value = mock_collection
        
        stats = await rag_service.get_statistics()
        
        assert stats["total_documents"] == 150
        assert stats["vector_store_type"] == "chromadb"
        assert stats["embedding_model"] is not None
        assert stats["llm_model"] is not None
        assert "index_size_mb" in stats
    
    @pytest.mark.asyncio
    async def test_clear_index(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test clearing the entire index."""
        await rag_service.initialize()
        
        mock_collection = MagicMock()
        mock_collection.delete = MagicMock()
        mock_collection.get = MagicMock(return_value={"ids": ["doc1", "doc2", "doc3"]})
        rag_service.chroma_client.get_or_create_collection.return_value = mock_collection
        
        result = await rag_service.clear_index()
        
        assert result["status"] == "success"
        assert result["documents_deleted"] == 3
        mock_collection.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_shutdown(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test RAG service shutdown."""
        await rag_service.initialize()
        
        # Verify components are initialized
        assert rag_service.vector_index is not None
        assert rag_service.query_engine is not None
        
        await rag_service.shutdown()
        
        # Verify components are cleaned up
        assert rag_service.vector_index is None
        assert rag_service.query_engine is None
        assert rag_service.chroma_client is None
        assert rag_service.vector_store is None
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index, sample_nodes
    ):
        """Test handling concurrent queries."""
        await rag_service.initialize()
        
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "Concurrent response"
        mock_response.source_nodes = sample_nodes
        mock_query_engine.query = AsyncMock(return_value=mock_response)
        rag_service.query_engine = mock_query_engine
        
        # Execute multiple queries concurrently
        import asyncio
        queries = ["Query 1", "Query 2", "Query 3", "Query 4", "Query 5"]
        results = await asyncio.gather(*[
            rag_service.query(q) for q in queries
        ])
        
        assert len(results) == 5
        for result in results:
            assert result["response"] == "Concurrent response"
            assert "sources" in result
        
        assert mock_query_engine.query.call_count == 5
    
    @pytest.mark.asyncio
    async def test_query_with_custom_top_k(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index, sample_nodes
    ):
        """Test query with custom top_k parameter."""
        await rag_service.initialize()
        
        # Should update retriever configuration
        result = await rag_service.query("Test query", top_k=10)
        
        # Verify the query was processed (implementation specific)
        assert "response" in result
        assert "sources" in result
    
    @pytest.mark.asyncio
    async def test_error_recovery(
        self, rag_service, mock_ollama, mock_chroma_client,
        mock_vector_store, mock_vector_index
    ):
        """Test error recovery and retry logic."""
        await rag_service.initialize()
        
        mock_query_engine = MagicMock()
        
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.response = "Success after retry"
        mock_response.source_nodes = []
        
        mock_query_engine.query = AsyncMock(
            side_effect=[Exception("Temporary failure"), mock_response]
        )
        rag_service.query_engine = mock_query_engine
        
        # Should retry and succeed
        with patch('services.rag_service.asyncio.sleep', new_callable=AsyncMock):
            result = await rag_service.query_with_retry("Test query", max_retries=2)
        
        assert result["response"] == "Success after retry"
        assert mock_query_engine.query.call_count == 2