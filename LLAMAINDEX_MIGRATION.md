# LlamaIndex Migration Guide

This document outlines the migration from LangChain to LlamaIndex in the RAG Financial AI project.

## 🔄 What Changed

### Dependencies
- **Removed**: `langchain`, `langchain-openai`, `faiss-cpu`
- **Added**: `llama-index`, `llama-index-llms-openai`, `llama-index-embeddings-openai`, `llama-index-vector-stores-chroma`, `llama-index-readers-file`

### Architecture Changes

#### 1. RAG Service (`services/rag_service.py`)
- **Before**: Custom RAG pipeline with LangChain components
- **After**: LlamaIndex-native components:
  - `VectorStoreIndex` for document indexing
  - `VectorIndexRetriever` for document retrieval  
  - `RetrieverQueryEngine` for query processing
  - `SimilarityPostprocessor` for filtering results

#### 2. Document Processing (`utils/document_processor.py`)
- **Before**: Manual text extraction with PyPDF2, python-docx, BeautifulSoup
- **After**: LlamaIndex readers:
  - `PDFReader` for PDF files
  - `DocxReader` for Word documents
  - `HTMLTagReader` for HTML files
  - `MarkdownReader` for Markdown files
  - `SentenceSplitter` for intelligent text chunking

#### 3. Vector Storage
- **Before**: Separate `VectorService` class with manual ChromaDB integration
- **After**: LlamaIndex `ChromaVectorStore` integration directly in RAG service

#### 4. LLM Integration
- **Before**: Separate `LLMService` with custom OpenAI client
- **After**: LlamaIndex `OpenAI` LLM wrapper with global settings

## 🚀 Key Improvements

### 1. Simplified Architecture
```python
# Before (multiple services)
class RAGService:
    def __init__(self):
        self.vector_service = VectorService()
        self.llm_service = LLMService()
        self.embedding_model = SentenceTransformer()

# After (unified LlamaIndex approach)
class RAGService:
    def __init__(self):
        Settings.llm = OpenAI(model="gpt-3.5-turbo")
        Settings.embed_model = OpenAIEmbedding()
        self.vector_index = VectorStoreIndex.from_vector_store(...)
```

### 2. Better Document Processing
```python
# Before (manual extraction)
if file_extension == '.pdf':
    text = await self._extract_pdf_text(file_path)
elif file_extension == '.docx':
    text = await self._extract_docx_text(file_path)
# ... more manual extractions

# After (LlamaIndex readers)
documents = self.pdf_reader.load_data(file=file_path)
nodes = self.text_splitter.get_nodes_from_documents(documents)
```

### 3. Enhanced Query Processing
```python
# Before (manual retrieval + generation)
retrieved_docs = await self.vector_service.similarity_search(...)
response = await self.llm_service.generate_response(query, context)

# After (integrated pipeline)
response = self.query_engine.query(query)
```

## 🔧 Configuration Changes

### Environment Variables
- `EMBEDDING_MODEL`: Changed from `sentence-transformers/all-MiniLM-L6-v2` to `text-embedding-ada-002`
- Added OpenAI API key requirement for both LLM and embeddings

### Dependencies
Update `requirements.txt`:
```bash
# Remove
langchain==0.0.340
langchain-openai==0.0.1
faiss-cpu==1.7.4

# Add
llama-index==0.9.20
llama-index-llms-openai==0.1.5
llama-index-embeddings-openai==0.1.5
llama-index-vector-stores-chroma==0.1.4
llama-index-readers-file==0.1.4
```

## 📊 Performance Improvements

1. **Faster Document Processing**: LlamaIndex readers are optimized for various file formats
2. **Better Chunking**: `SentenceSplitter` provides smarter text segmentation
3. **Integrated Retrieval**: Single query engine handles retrieval and generation
4. **Post-processing**: Built-in similarity filtering and response enhancement

## 🔍 New Features

1. **Advanced Query Engines**: Support for various query strategies
2. **Post-processors**: Similarity filtering, reranking capabilities
3. **Better Metadata Handling**: Automatic metadata propagation through pipeline
4. **Extensible Architecture**: Easy to add new retrievers and processors

## 📚 LlamaIndex Resources

- [LlamaIndex Documentation](https://docs.llamaindex.ai/en/stable/)
- [Query Engines Guide](https://docs.llamaindex.ai/en/stable/module_guides/deploying/query_engine/)
- [Vector Stores](https://docs.llamaindex.ai/en/stable/module_guides/storing/vector_stores/)
- [Document Readers](https://docs.llamaindex.ai/en/stable/module_guides/loading/connector/)

## 🚀 Next Steps

1. **Advanced Retrievers**: Implement hybrid search, keyword + semantic
2. **Reranking**: Add reranking models for better result quality
3. **Agents**: Leverage LlamaIndex agents for complex financial analysis
4. **Evaluation**: Use LlamaIndex evaluation framework for RAG quality metrics

This migration positions the project to leverage LlamaIndex's advanced RAG capabilities while maintaining the existing API and user experience.
