# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Financial AI is a production-ready RAG (Retrieval-Augmented Generation) system for financial document analysis using the GPT-OSS:20B model (open-source 20B parameter LLM) served locally via Ollama. The system consists of a FastAPI backend with LlamaIndex integration and a Next.js frontend, designed for enterprise-grade financial document processing and Q&A.

**Note:** This is a learning project focused on understanding RAG pipelines, vector databases, and modern AI application development. See [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for educational insights and comprehensive evaluation.

## Learning Resources

Comprehensive documentation and visual guides for understanding this project:

- **[LEARNING_GUIDE.md](LEARNING_GUIDE.md)** - Educational evaluation with Mermaid diagrams explaining RAG concepts, what you built well, and learning opportunities (Score: 9/10)
- **[LEARNING_GUIDE.html](LEARNING_GUIDE.html)** - Beautiful browser-viewable version with rendered diagrams
- **[ARCHITECTURE_VISUAL.md](ARCHITECTURE_VISUAL.md)** - Visual architecture documentation with 20+ Mermaid diagrams showing system flow, database schemas, and component interactions
- **[ARCHITECTURE_VISUAL.html](ARCHITECTURE_VISUAL.html)** - Browser-viewable architecture diagrams
- **[.claude/skills/](.claude/skills/)** - Reusable Claude Code skills for development workflows

## Architecture

The system follows a microservices architecture:

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend**: FastAPI with LlamaIndex RAG framework, ChromaDB vector storage
- **AI Model**: GPT-OSS:20B served locally via Ollama
- **Database**: ChromaDB for vector embeddings, SQLite for metadata
- **Deployment**: Docker containers with nginx proxy

## Development Commands

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py          # Development server (http://localhost:8000)
# Alternative: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev         # Development server (http://localhost:3000)
npm run build       # Production build
npm run start       # Production server
npm run lint        # ESLint
npm run type-check  # TypeScript checking
npm test            # Jest unit tests
npm run test:watch  # Jest in watch mode
npm run test:e2e    # Playwright end-to-end tests
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/ -v --cov=.

# Frontend tests  
cd frontend
npm test            # Jest unit tests
npm run test:e2e    # Playwright e2e tests
```

### Code Quality
```bash
# Backend linting/formatting (available via requirements.txt)
cd backend
black .             # Code formatting
isort .             # Import sorting
flake8 .            # Linting

# Frontend linting/type checking
cd frontend
npm run lint        # ESLint
npm run type-check  # TypeScript
```

### Development Scripts
```bash
./scripts/setup.sh  # Initial project setup (creates directories, checks dependencies)
./scripts/dev.sh    # Start all services in development mode (requires Ollama running)
```

### Claude Code Skills (`.claude/skills/`)

Reusable development skills - invoke by asking Claude Code:

```bash
# Quick system health check - verifies Ollama, backend, ChromaDB, Redis
"Run rag-debug skill"
"Check system health"

# Fast test suite for development - runs important tests, skips slow integration tests
"Run quick-test skill"
"Test my changes quickly"

# Educational explanations of RAG concepts with code examples
"Explain how RAG works"
"How does the document processing work?"
```

### Single Test Commands
```bash
# Backend single test
cd backend
pytest tests/test_specific_file.py::test_function_name -v

# Frontend single test
cd frontend
npm test -- --testNamePattern="specific test name"
npm test -- --testPathPattern="specific/test/file"
```

### Docker Commands
```bash
docker-compose up --build                    # Development environment
docker-compose -f docker-compose.prod.yml up # Production environment
```

## Core Architecture Components

### Backend (`backend/`)
- **`main.py`**: FastAPI application entry point with CORS and global exception handling
- **`core/config.py`**: Centralized configuration using Pydantic settings from environment variables
- **`services/rag_service.py`**: LlamaIndex-based RAG implementation with GPT-OSS:20B integration
- **`services/chat_service.py`**: Chat session management and conversation handling
- **`services/document_service.py`**: Document upload, processing, and metadata management
- **`utils/document_processor.py`**: Document parsing and chunking using LlamaIndex readers
- **`api/routes/`**: RESTful API endpoints for chat, documents, and health monitoring

### Frontend (`frontend/src/`)
- **`app/`**: Next.js 14 App Router pages and layouts
- **`components/`**: Reusable React components (chat interface, document management, UI components)
- **`lib/api.ts`**: Axios-based API client with interceptors and typed endpoints
- **`lib/query-provider.tsx`**: React Query setup for data fetching and caching
- **`types/index.ts`**: TypeScript type definitions for API responses and data models

### Key Integrations
- **LlamaIndex**: RAG framework handling document ingestion, chunking, vector storage, and query processing
- **Ollama**: Local LLM serving for GPT-OSS:20B model with configurable parameters
- **ChromaDB**: Vector database for document embeddings with persistent storage
- **HuggingFace Embeddings**: Local sentence transformers for document embedding generation

## Environment Configuration

Required environment variables (see `env.example`):

### Ollama/Model Configuration
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `GPT_OSS_MODEL`: Model name (default: gpt-oss:20b)
- `MAX_TOKENS`: Maximum tokens per response (default: 2048)
- `TEMPERATURE`: Model temperature (default: 0.1)

### Vector Database
- `VECTOR_DB_TYPE`: Database type (default: chromadb)
- `CHROMA_PERSIST_DIRECTORY`: ChromaDB storage path
- `EMBEDDING_MODEL`: HuggingFace embedding model name

### Document Processing
- `CHUNK_SIZE`: Text chunk size for processing (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 50)

## Prerequisites for Development

### Required Dependencies
1. **Ollama**: Install from https://ollama.com/download
2. **GPT-OSS:20B Model**: Run `ollama pull gpt-oss:20b`
3. **Python 3.9+** with pip
4. **Node.js 18+** with npm
5. **Docker & Docker Compose** (for containerized deployment)

### Development Setup
1. Use setup script for initial configuration: `./scripts/setup.sh`
2. Ensure Ollama is running: `ollama serve`
3. Verify GPT-OSS:20B model is available: `ollama list`
4. Copy and configure environment: `cp env.example .env`
5. Start development servers: `./scripts/dev.sh` (or manually start backend/frontend)

### Quick Start Development
```bash
# Automated setup and start
./scripts/setup.sh && ./scripts/dev.sh

# Manual setup
ollama serve &
cd backend && python main.py &
cd frontend && npm run dev
```

## Important Implementation Notes

### RAG Pipeline (`backend/services/rag_service.py`)
- Uses LlamaIndex's VectorStoreIndex for document management
- ChromaVectorStore integration for persistent embeddings
- RetrieverQueryEngine with similarity post-processing
- Custom confidence calculation from source node similarity scores
- Graceful error handling for Ollama connection issues

### Document Processing (`backend/utils/document_processor.py`)
- Supports PDF, DOCX, TXT, HTML, MD formats via LlamaIndex readers
- Intelligent chunking using LlamaIndex SentenceSplitter
- Metadata preservation for source tracking and filtering
- Asynchronous processing for large documents

### Frontend State Management (`frontend/src/`)
- **React Query** (`@tanstack/react-query`): Server state management and caching
- **Zustand**: Local UI state management 
- **React Hook Form**: Form handling and validation
- **React Dropzone**: File upload handling
- **Axios**: API client with interceptors (`lib/api.ts`)
- **shadcn/ui + Radix UI**: Component library with accessibility

### API Design
- RESTful endpoints following OpenAPI 3.0 standards
- Automatic API documentation at `/docs` (Swagger UI)
- Error handling with appropriate HTTP status codes
- CORS configuration for cross-origin requests

## Common Development Workflows

### Adding New Document Types
1. Update `ALLOWED_FILE_TYPES` in `backend/core/config.py`
2. Add LlamaIndex reader in `backend/utils/document_processor.py`
3. Update frontend file type validation in upload components

### Modifying RAG Behavior
1. Adjust retrieval parameters in `backend/services/rag_service.py`
2. Modify chunking strategy in document processor
3. Update similarity thresholds and top-k values
4. Test with representative documents

### Extending API Endpoints
1. Create new route module in `backend/api/routes/`
2. Define Pydantic models for request/response validation
3. Add route to main.py router inclusion
4. Update frontend API client in `lib/api.ts`

### Frontend Component Development
1. Follow existing component patterns in `components/`
2. Use shadcn/ui components for consistency
3. Implement proper TypeScript typing
4. Add React Query mutations for API interactions

## Testing Strategy

### Backend Tests
- Unit tests for individual service methods
- Integration tests for RAG pipeline
- API endpoint testing with FastAPI test client
- Mocking of external dependencies (Ollama, ChromaDB)

### Frontend Tests
- Component unit tests with Jest and React Testing Library
- E2E tests with Playwright for user workflows
- API integration tests with mocked responses

## Deployment Considerations

### Local Development
- Requires Ollama running locally with GPT-OSS:20B model
- ChromaDB data persisted to local filesystem
- Hot reloading enabled for both frontend and backend

### Production Deployment
- Docker containers for consistent environments
- Nginx reverse proxy for SSL termination and routing
- Persistent volumes for vector database storage
- Environment-specific configuration management
- Health check endpoints for monitoring

## Troubleshooting

### Quick Diagnostic

Run the automated health check for comprehensive system diagnostics:

```bash
# Ask Claude Code to run the health check
"Run rag-debug skill"

# This checks:
# ✓ Ollama service status and GPT-OSS:20B model availability
# ✓ Backend API connectivity
# ✓ ChromaDB vector database and document count
# ✓ Redis cache connection (optional)
# ✓ End-to-end RAG query test
```

### Common Issues

- **Ollama Connection Errors**: Verify Ollama is running (`ollama serve`) and model is installed (`ollama list`)
- **Model Not Found**: Run `ollama pull gpt-oss:20b` to download the model (~8GB, takes 10-20 minutes)
- **File Upload Failures**: Check file size limits in `backend/core/config.py` and supported formats
- **Vector Search Issues**: Ensure documents are properly indexed and ChromaDB is accessible in `vector-store/`
- **Frontend API Errors**: Verify backend URL configuration and CORS settings in `backend/main.py`
- **Port Conflicts**: Backend uses :8000, Frontend uses :3000, Ollama uses :11434
- **Virtual Environment Issues**: Ensure backend venv is activated before running Python commands
- **Slow First Query**: First query loads the model into memory (~10s), subsequent queries are faster (~2-3s)

### Development Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Ollama API**: http://localhost:11434

## Key Files Quick Reference

**RAG Pipeline Core:**
- `backend/services/rag_service.py:158-223` - Main query logic with error handling and fallback mechanisms
- `backend/services/rag_service.py:115-120` - Retriever configuration (top_k=10, similarity_cutoff=0.7)
- `backend/utils/document_processor.py` - Document chunking (size=1000, overlap=200) and embedding generation
- `backend/core/config.py:115-120` - Configuration validation with cross-field checks

**Frontend Patterns:**
- `frontend/src/components/chat/chat-interface.tsx:45-55` - React Query mutation pattern for API calls
- `frontend/src/lib/api.ts` - Axios client configuration with interceptors
- `frontend/src/lib/query-provider.tsx` - React Query setup and configuration

**Documentation:**
- `LEARNING_GUIDE.md` - Comprehensive project evaluation with RAG concepts explained
- `ARCHITECTURE_VISUAL.md` - System architecture with 20+ Mermaid diagrams
- `.claude/skills/` - Reusable development skills (rag-debug, quick-test, explain-rag)