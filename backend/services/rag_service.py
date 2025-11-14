"""
RAG (Retrieval-Augmented Generation) service implementation using LlamaIndex with GPT-OSS:20B.
"""
from typing import List, Dict, Any, Optional
import logging
import asyncio
import time
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from core.config import settings
from core.logging import get_logger
from core.exceptions import (
    RAGPipelineError,
    VectorStoreError,
    OllamaConnectionError,
    ServiceInitializationError
)

logger = get_logger("rag_service")


class RAGService:
    """RAG service for document retrieval and generation using LlamaIndex."""
    
    def __init__(self, cache_service=None):
        self.vector_index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.chroma_client = None
        self.vector_store = None
        self.cache_service = cache_service
        
    async def initialize(self):
        """Initialize the RAG service with LlamaIndex components and GPT-OSS:20B."""
        logger.info("Initializing RAG service with LlamaIndex and GPT-OSS:20B...")
        
        # Configure LlamaIndex settings for Ollama GPT-OSS:20B
        Settings.llm = Ollama(
            model=settings.GPT_OSS_MODEL,
            base_url=str(settings.OLLAMA_BASE_URL),  # Convert to string
            temperature=settings.TEMPERATURE,
            request_timeout=120.0  # GPT-OSS models may need more time
        )
        
        # Configure local embedding model
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY
        )
        
        # Get or create collection
        collection = self.chroma_client.get_or_create_collection(
            name="financial_documents"
        )
        
        # Create vector store
        self.vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Create or load index
        # Check if collection has any data
        if collection.count() > 0:
            try:
                self.vector_index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store,
                    storage_context=storage_context
                )
                logger.info(f"Loaded existing vector index with {collection.count()} documents")
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
                self.vector_index = VectorStoreIndex([], storage_context=storage_context)
                logger.info("Created new vector index")
        else:
            # Create new index if collection is empty
            self.vector_index = VectorStoreIndex([], storage_context=storage_context)
            logger.info("Created new vector index (collection was empty)")
        
        # Create query engine
        self._setup_query_engine()
        
        logger.info("RAG service initialized successfully")
    
    async def shutdown(self):
        """Shutdown the RAG service and cleanup resources."""
        logger.info("Shutting down RAG service...")
        
        try:
            # Close ChromaDB client if needed
            if self.chroma_client:
                # ChromaDB client doesn't have explicit close method
                self.chroma_client = None
                
            # Reset other components
            self.vector_index = None
            self.query_engine = None
            self.vector_store = None
            
            logger.info("RAG service shutdown complete")
        except Exception as e:
            logger.error(f"Error during RAG service shutdown: {e}")
            raise
    
    def _setup_query_engine(self):
        """Setup the query engine with custom retrievers and post-processors."""
        if not self.vector_index:
            return
            
        # Use the vector index's built-in query engine 
        # This avoids ChromaDB where clause issues
        self.query_engine = self.vector_index.as_query_engine(
            similarity_top_k=10,
            response_mode="compact"
        )
    
    async def process_query(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process a query using LlamaIndex RAG pipeline.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score for retrieval
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()
        
        # Check cache if enabled
        if use_cache and self.cache_service:
            try:
                cached_result = await self.cache_service.get_query_result(
                    query, 
                    filters={"top_k": top_k, "threshold": score_threshold}
                )
                if cached_result:
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    cached_result["cached"] = True
                    cached_result["processing_time"] = time.time() - start_time
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
        
        try:
            if not self.query_engine:
                return {
                    "response": "RAG service is not properly initialized. Please ensure Ollama is running with GPT-OSS:20B model.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Check if we have any documents in the index
            collection_count = 0
            try:
                if self.chroma_client:
                    collection = self.chroma_client.get_collection("financial_documents")
                    collection_count = collection.count()
                    logger.info(f"Found collection with {collection_count} documents")
            except Exception as e:
                logger.info(f"No collection found or error checking collection: {e}")
                collection_count = 0
            
            # Re-create query engine with new top_k if needed
            if top_k != 10:  # Only recreate if different from default
                self.query_engine = self.vector_index.as_query_engine(
                    similarity_top_k=top_k,
                    response_mode="compact"
                )
            
            # Execute query using LlamaIndex query engine
            # If we have documents, use RAG pipeline; otherwise use LLM directly
            try:
                if collection_count > 0:
                    # We have documents - use RAG query engine
                    logger.info("Using RAG approach with document context")
                    response = self.query_engine.query(query)
                else:
                    # No documents - use LLM directly for general chat
                    logger.info("Using general chat mode - no document context")
                    llm_response = Settings.llm.complete(query)
                    # Create a response object compatible with our processing
                    class DirectLLMResponse:
                        def __init__(self, text):
                            self.response = text
                            self.source_nodes = []
                        def __str__(self):
                            return str(self.response)
                    
                    response = DirectLLMResponse(str(llm_response))
                
            except Exception as query_error:
                logger.error(f"Error in query execution: {query_error}")
                # Check if it's an Ollama connection error
                if "connection" in str(query_error).lower() or "ollama" in str(query_error).lower():
                    raise OllamaConnectionError(f"Failed to connect to Ollama: {query_error}")
                
                # Provide a fallback response
                class FallbackResponse:
                    def __init__(self, text, source_nodes=None):
                        self.response = text
                        self.source_nodes = source_nodes or []
                    def __str__(self):
                        return str(self.response)
                
                response = FallbackResponse(
                    "I encountered an error processing your query. Please ensure documents are uploaded and try again.",
                    []
                )
            
            # Extract sources from source nodes
            sources = []
            for node in response.source_nodes:
                if hasattr(node, 'metadata') and 'source' in node.metadata:
                    sources.append(node.metadata['source'])
                elif hasattr(node, 'metadata') and 'filename' in node.metadata:
                    sources.append(node.metadata['filename'])
            
            # Calculate confidence based on similarity scores
            confidence = self._calculate_confidence_from_nodes(response.source_nodes)
            
            # Extract response text - LlamaIndex response objects have .response attribute
            response_text = response.response if hasattr(response, 'response') else str(response)
            
            result = {
                "response": response_text,
                "sources": list(set(sources)),  # Remove duplicates
                "confidence": confidence,
                "retrieved_chunks": len(response.source_nodes),
                "processing_time": time.time() - start_time,
                "cached": False
            }
            
            # Cache the result if cache is enabled
            if self.cache_service and use_cache:
                try:
                    await self.cache_service.set_query_result(
                        query,
                        result,
                        filters={"top_k": top_k, "threshold": score_threshold}
                    )
                    logger.debug(f"Cached query result: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            # Check if it's an Ollama connection error
            if "connection" in str(e).lower() or "ollama" in str(e).lower():
                return {
                    "response": "Unable to connect to Ollama. Please ensure Ollama is running and the GPT-OSS:20B model is installed.",
                    "sources": [],
                    "confidence": 0.0
                }
            raise
    
    def _calculate_confidence_from_nodes(self, source_nodes) -> float:
        """Calculate confidence score from LlamaIndex source nodes."""
        if not source_nodes:
            return 0.0
        
        # Extract similarity scores from nodes
        scores = []
        for node in source_nodes:
            if hasattr(node, 'score') and node.score is not None:
                scores.append(node.score)
        
        if not scores:
            # If no scores available, return moderate confidence
            return 0.7
        
        # Use average similarity score as confidence
        return sum(scores) / len(scores)
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to the vector index.
        
        Args:
            documents: List of document dictionaries with content and metadata
        """
        try:
            from llama_index.core.schema import Document, TextNode
            
            if not self.vector_index:
                logger.error("Vector index not initialized - attempting to reinitialize")
                # Try to reinitialize if index is missing
                await self.initialize()
                if not self.vector_index:
                    logger.error("Failed to initialize vector index")
                    return
            
            # Convert documents to LlamaIndex Document objects
            llama_docs = []
            for doc in documents:
                # Create TextNode with content and metadata
                node = TextNode(
                    text=doc["content"],
                    metadata={
                        "document_id": doc["document_id"],
                        "source": doc["source"],
                        "filename": doc.get("filename", ""),
                        "file_type": doc.get("file_type", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "created_at": doc.get("created_at", "")
                    }
                )
                node.id_ = doc["id"]
                llama_docs.append(node)
            
            # Add documents to index
            self.vector_index.insert_nodes(llama_docs)
            
            # Refresh query engine after adding documents
            self._setup_query_engine()
            
            logger.info(f"Added {len(llama_docs)} documents to vector index")
            
        except Exception as e:
            logger.error(f"Error adding documents to index: {e}")
            raise
    
    async def delete_documents(self, document_id: str):
        """
        Delete documents by document_id from ChromaDB.
        
        Uses ChromaDB's native API directly since LlamaIndex doesn't support
        deletion by metadata at the index level.
        
        Args:
            document_id: ID of the document to delete
            
        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            if not self.chroma_client:
                raise VectorStoreError("ChromaDB client not initialized")
            
            collection = self.chroma_client.get_collection("financial_documents")
            
            # First, check if any documents exist with this document_id
            results = collection.get(
                where={"document_id": document_id},
                include=["ids"]
            )
            
            if not results["ids"]:
                logger.warning(f"No chunks found for document {document_id}")
                return
            
            # Delete all chunks for this document using ChromaDB's native API
            collection.delete(where={"document_id": document_id})
            
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            # Refresh query engine after deletion to ensure consistency
            self._setup_query_engine()
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise VectorStoreError(f"Failed to delete documents: {e}")
    
    async def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and GPT-OSS:20B model is available."""
        try:
            import requests
            
            # Check if Ollama is running
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": "Ollama is not running or not accessible",
                    "ollama_running": False,
                    "model_available": False
                }
            
            # Check if GPT-OSS:20B model is available
            models = response.json().get("models", [])
            gpt_oss_available = any(
                model.get("name", "").startswith("gpt-oss") 
                for model in models
            )
            
            return {
                "status": "success" if gpt_oss_available else "warning",
                "message": "GPT-OSS:20B model is available" if gpt_oss_available else "GPT-OSS:20B model not found",
                "ollama_running": True,
                "model_available": gpt_oss_available,
                "available_models": [model.get("name") for model in models]
            }
            
        except Exception as e:
            logger.error(f"Error checking Ollama status: {e}")
            return {
                "status": "error",
                "message": f"Error checking Ollama status: {str(e)}",
                "ollama_running": False,
                "model_available": False
            }
