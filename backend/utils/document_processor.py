"""
Document processing utilities using LlamaIndex readers and chunking.
"""
import os
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from llama_index.core import Document
from llama_index.readers.file import PDFReader, DocxReader, HTMLTagReader, MarkdownReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from core.config import settings

logger = logging.getLogger("rag_financial_ai")


class DocumentProcessor:
    """Document processing and chunking utility using LlamaIndex."""
    
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        
        # Initialize LlamaIndex readers
        self.pdf_reader = PDFReader()
        self.docx_reader = DocxReader()
        self.html_reader = HTMLTagReader()
        self.markdown_reader = MarkdownReader()
        
        # Initialize text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    async def initialize(self):
        """Initialize the document processor."""
        logger.info("Document processor initialized with LlamaIndex readers")
    
    async def process_file(
        self,
        file_path: Path,
        document_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Process a file using LlamaIndex readers and return document chunks.
        
        Args:
            file_path: Path to the file
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            List of document chunks ready for vector store
        """
        try:
            # Load document using appropriate LlamaIndex reader
            documents = await self._load_document_with_reader(file_path)
            
            if not documents:
                raise ValueError(f"No content extracted from {filename}")
            
            # Add metadata to documents
            for doc in documents:
                doc.metadata.update({
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": file_path.suffix.lower(),
                    "source": str(file_path),
                    "created_at": datetime.utcnow().isoformat()
                })
            
            # Split documents into chunks using LlamaIndex
            nodes = self.text_splitter.get_nodes_from_documents(documents)
            
            # Convert nodes to our format
            chunks = []
            for i, node in enumerate(nodes):
                chunk_dict = {
                    "id": f"{document_id}_chunk_{i}",
                    "document_id": document_id,
                    "content": node.text,
                    "chunk_index": i,
                    "source": str(file_path),
                    "filename": filename,
                    "file_type": file_path.suffix.lower(),
                    "created_at": datetime.utcnow().isoformat()
                }
                chunks.append(chunk_dict)
            
            logger.info(f"Processed {filename}: created {len(chunks)} chunks using LlamaIndex")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise
    
    async def _load_document_with_reader(self, file_path: Path) -> List[Document]:
        """Load document using appropriate LlamaIndex reader."""
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.pdf':
                documents = self.pdf_reader.load_data(file=file_path)
            elif file_extension == '.docx':
                documents = self.docx_reader.load_data(file=file_path)
            elif file_extension in ['.html', '.htm']:
                documents = self.html_reader.load_data(file=file_path)
            elif file_extension == '.md':
                documents = self.markdown_reader.load_data(file=file_path)
            elif file_extension == '.txt':
                # For TXT files, create document manually
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents = [Document(text=content)]
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document with reader: {e}")
            raise
    
    async def get_document_summary(self, file_path: Path) -> str:
        """Generate a summary of the document content."""
        try:
            documents = await self._load_document_with_reader(file_path)
            
            if not documents:
                return "No content available for summary"
            
            # Combine all document text
            full_text = "\n".join([doc.text for doc in documents])
            
            # Return first 500 characters as preview
            if len(full_text) > 500:
                return full_text[:500] + "..."
            else:
                return full_text
                
        except Exception as e:
            logger.error(f"Error generating document summary: {e}")
            return f"Error processing document: {str(e)}"
