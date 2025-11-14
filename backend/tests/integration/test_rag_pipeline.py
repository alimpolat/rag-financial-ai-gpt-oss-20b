"""Integration tests for the complete RAG pipeline."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
from typing import Dict, List, Any

from services.rag_service import RAGService
from services.document_service import DocumentService
from services.chat_service import ChatService
from utils.document_processor import DocumentProcessor
from core.config import settings


@pytest.fixture
def temp_vector_dir():
    """Create temporary directory for vector storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing."""
    client = MagicMock()
    
    # Mock model listing
    client.list.return_value = {
        'models': [{'name': 'gpt-oss:20b'}]
    }
    
    # Mock chat response
    async def mock_chat(*args, **kwargs):
        return {
            'message': {
                'content': 'Based on the documents, the answer is 42.'
            }
        }
    client.chat = AsyncMock(side_effect=mock_chat)
    
    return client


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model."""
    model = MagicMock()
    model.encode.return_value = [[0.1] * 768]  # Mock 768-dim embedding
    return model


@pytest.fixture
async def rag_pipeline(temp_vector_dir, mock_ollama_client, mock_embedding_model):
    """Set up complete RAG pipeline with mocked dependencies."""
    with patch('services.rag_service.chromadb.PersistentClient') as mock_chroma, \
         patch('services.rag_service.HuggingFaceEmbeddings') as mock_hf_embed, \
         patch('services.rag_service.Ollama') as mock_ollama_cls, \
         patch('utils.document_processor.PyPDFReader') as mock_pdf_reader:
        
        # Configure mocks
        mock_hf_embed.return_value = mock_embedding_model
        mock_ollama_cls.return_value = mock_ollama_client
        
        # Mock ChromaDB
        mock_collection = MagicMock()
        mock_collection.add = MagicMock()
        mock_collection.query = MagicMock(return_value={
            'documents': [['Test document content']],
            'metadatas': [[{'source': 'test.pdf', 'page': 1}]],
            'distances': [[0.1]]
        })
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
        
        # Mock PDF reader
        mock_pdf_reader.return_value.load_data.return_value = [
            MagicMock(text='This is test content from the PDF.', metadata={'page': 1})
        ]
        
        # Initialize services
        rag_service = RAGService()
        await rag_service.initialize()
        
        document_service = DocumentService()
        chat_service = ChatService(rag_service)
        
        return {
            'rag': rag_service,
            'document': document_service,
            'chat': chat_service,
            'mocks': {
                'chroma': mock_chroma,
                'collection': mock_collection,
                'embedding': mock_embedding_model,
                'ollama': mock_ollama_client
            }
        }


class TestRAGPipelineIntegration:
    """Test complete RAG pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_document_processing_and_query(self, rag_pipeline, tmp_path):
        """Test complete flow from document upload to query."""
        # Create a test PDF file
        test_pdf = tmp_path / "test_financial_report.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\nTest PDF content')
        
        # Step 1: Process document
        with patch('utils.document_processor.PyPDFReader') as mock_reader:
            mock_reader.return_value.load_data.return_value = [
                MagicMock(
                    text='Company revenue was $10 million in Q1 2024.',
                    metadata={'page': 1, 'filename': 'test_financial_report.pdf'}
                ),
                MagicMock(
                    text='Expenses totaled $6 million, resulting in $4 million profit.',
                    metadata={'page': 2, 'filename': 'test_financial_report.pdf'}
                )
            ]
            
            processor = DocumentProcessor()
            chunks = await processor.process_document(str(test_pdf))
            
            # Verify chunks were created
            assert len(chunks) > 0
            assert any('revenue' in chunk.text.lower() for chunk in chunks)
        
        # Step 2: Add chunks to vector store
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Simulate adding to index
        for i, chunk in enumerate(chunks):
            mock_collection.add.assert_called()
        
        # Step 3: Query the system
        mock_collection.query.return_value = {
            'documents': [['Company revenue was $10 million in Q1 2024.']],
            'metadatas': [[{'source': 'test_financial_report.pdf', 'page': 1}]],
            'distances': [[0.05]]
        }
        
        response = await rag_service.query(
            "What was the company revenue in Q1 2024?"
        )
        
        # Verify response
        assert response is not None
        assert 'response' in response
        assert response['confidence'] > 0
        assert len(response['sources']) > 0
        assert response['sources'][0]['filename'] == 'test_financial_report.pdf'
    
    @pytest.mark.asyncio
    async def test_multi_document_context_aggregation(self, rag_pipeline):
        """Test querying across multiple documents."""
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Mock multiple document results
        mock_collection.query.return_value = {
            'documents': [[
                'Q1 revenue: $10M',
                'Q2 revenue: $12M', 
                'Q3 revenue: $15M'
            ]],
            'metadatas': [[
                {'source': 'q1_report.pdf', 'page': 5},
                {'source': 'q2_report.pdf', 'page': 3},
                {'source': 'q3_report.pdf', 'page': 7}
            ]],
            'distances': [[0.1, 0.15, 0.2]]
        }
        
        response = await rag_service.query(
            "Show me quarterly revenue trends"
        )
        
        # Verify aggregated context
        assert response is not None
        assert len(response['sources']) == 3
        assert response['confidence'] > 0.7  # Good confidence with multiple sources
        
        # Check source diversity
        sources = [s['filename'] for s in response['sources']]
        assert 'q1_report.pdf' in sources
        assert 'q2_report.pdf' in sources
        assert 'q3_report.pdf' in sources
    
    @pytest.mark.asyncio
    async def test_conversation_context_preservation(self, rag_pipeline):
        """Test that conversation context is maintained across queries."""
        chat_service = rag_pipeline['chat']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # First query
        mock_collection.query.return_value = {
            'documents': [['Company ABC had revenue of $10M']],
            'metadatas': [[{'source': 'report.pdf', 'page': 1}]],
            'distances': [[0.1]]
        }
        
        session_id = "test-session-123"
        response1 = await chat_service.process_message(
            session_id=session_id,
            message="What company are we discussing?",
            user_id="test-user"
        )
        
        # Second query - should maintain context
        response2 = await chat_service.process_message(
            session_id=session_id,
            message="What was their revenue?",
            user_id="test-user"
        )
        
        # Verify context was maintained
        history = await chat_service.get_chat_history(session_id)
        assert len(history) == 4  # 2 user messages + 2 assistant responses
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'
    
    @pytest.mark.asyncio
    async def test_concurrent_query_handling(self, rag_pipeline):
        """Test system handles concurrent queries correctly."""
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Mock responses for different queries
        query_responses = {
            'revenue': {
                'documents': [['Revenue was $10M']],
                'metadatas': [[{'source': 'financial.pdf', 'page': 1}]],
                'distances': [[0.1]]
            },
            'expenses': {
                'documents': [['Expenses were $6M']],
                'metadatas': [[{'source': 'financial.pdf', 'page': 2}]],
                'distances': [[0.1]]
            }
        }
        
        def mock_query_side_effect(*args, **kwargs):
            query_text = kwargs.get('query_texts', [''])[0].lower()
            if 'revenue' in query_text:
                return query_responses['revenue']
            elif 'expense' in query_text:
                return query_responses['expenses']
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        mock_collection.query.side_effect = mock_query_side_effect
        
        # Execute concurrent queries
        tasks = [
            rag_service.query("What was the revenue?"),
            rag_service.query("What were the expenses?"),
            rag_service.query("Calculate profit margin")
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all queries completed
        assert len(responses) == 3
        assert all(r is not None for r in responses)
        assert all('response' in r for r in responses)
    
    @pytest.mark.asyncio
    async def test_document_update_and_reindex(self, rag_pipeline):
        """Test updating documents and reindexing."""
        document_service = rag_pipeline['document']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Initial document
        doc_id = "doc-123"
        initial_chunks = [
            {'text': 'Old revenue: $8M', 'metadata': {'doc_id': doc_id}}
        ]
        
        # Update document
        updated_chunks = [
            {'text': 'Updated revenue: $10M', 'metadata': {'doc_id': doc_id}}
        ]
        
        # Simulate deletion of old chunks
        mock_collection.delete.return_value = None
        
        # Simulate addition of new chunks
        mock_collection.add.return_value = None
        
        # Perform update
        await document_service.update_document(doc_id, updated_chunks)
        
        # Verify old chunks deleted and new ones added
        mock_collection.delete.assert_called()
        mock_collection.add.assert_called()
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_pipeline(self, rag_pipeline):
        """Test pipeline handles and recovers from errors."""
        rag_service = rag_pipeline['rag']
        mock_ollama = rag_pipeline['mocks']['ollama']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Simulate vector search success but LLM failure
        mock_collection.query.return_value = {
            'documents': [['Test content']],
            'metadatas': [[{'source': 'test.pdf'}]],
            'distances': [[0.1]]
        }
        
        # First call fails
        mock_ollama.chat.side_effect = Exception("Model temporarily unavailable")
        
        response1 = await rag_service.query("Test query")
        assert response1 is None or 'error' in response1
        
        # Recovery - second call succeeds
        mock_ollama.chat.side_effect = None
        mock_ollama.chat.return_value = {
            'message': {'content': 'Recovered response'}
        }
        
        response2 = await rag_service.query("Test query")
        assert response2 is not None
        assert 'response' in response2
    
    @pytest.mark.asyncio
    async def test_relevance_filtering(self, rag_pipeline):
        """Test that irrelevant results are filtered out."""
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Mock results with varying relevance
        mock_collection.query.return_value = {
            'documents': [[
                'Highly relevant financial data',
                'Somewhat related information',
                'Completely unrelated content'
            ]],
            'metadatas': [[
                {'source': 'financial.pdf', 'page': 1},
                {'source': 'report.pdf', 'page': 5},
                {'source': 'random.pdf', 'page': 2}
            ]],
            'distances': [[0.1, 0.5, 0.9]]  # Lower is better
        }
        
        response = await rag_service.query(
            "Show financial data",
            similarity_threshold=0.6  # Filter out high distances
        )
        
        # Verify filtering worked
        assert response is not None
        assert len(response['sources']) <= 2  # Should filter out the third
        assert response['confidence'] > 0.5
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, rag_pipeline):
        """Test that document metadata is preserved through pipeline."""
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Rich metadata
        mock_collection.query.return_value = {
            'documents': [['Financial statement content']],
            'metadatas': [[{
                'source': 'annual_report_2024.pdf',
                'page': 42,
                'section': 'Income Statement',
                'date': '2024-03-31',
                'document_type': 'financial_report',
                'company': 'ABC Corp'
            }]],
            'distances': [[0.05]]
        }
        
        response = await rag_service.query("Show income statement")
        
        # Verify metadata preserved
        assert response is not None
        assert len(response['sources']) > 0
        source = response['sources'][0]
        assert source['filename'] == 'annual_report_2024.pdf'
        assert source['page'] == 42
        assert 'section' in source['metadata']
        assert source['metadata']['company'] == 'ABC Corp'
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, rag_pipeline):
        """Test caching integration in pipeline."""
        rag_service = rag_pipeline['rag']
        mock_collection = rag_pipeline['mocks']['collection']
        
        # Mock cache
        with patch('services.cache_service.CacheService') as mock_cache_cls:
            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            
            # First query - cache miss
            mock_cache.get_query_result.return_value = None
            
            mock_collection.query.return_value = {
                'documents': [['Cached content']],
                'metadatas': [[{'source': 'test.pdf'}]],
                'distances': [[0.1]]
            }
            
            response1 = await rag_service.query("Test query")
            
            # Verify cache was set
            mock_cache.set_query_result.assert_called_once()
            
            # Second query - cache hit
            mock_cache.get_query_result.return_value = {
                'response': 'Cached response',
                'sources': [{'filename': 'test.pdf'}],
                'confidence': 0.9,
                'cached': True
            }
            
            response2 = await rag_service.query("Test query")
            
            # Verify cached response used
            assert response2['cached'] is True
            assert mock_collection.query.call_count == 1  # Not called again