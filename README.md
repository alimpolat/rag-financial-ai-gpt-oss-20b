# RAG Financial AI Agent - GPT-OSS:20B

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-black?logo=next.js&logoColor=white)](https://nextjs.org/)

> A production-ready RAG (Retrieval-Augmented Generation) system for financial document analysis using the GPT-OSS:20B model (open-source 20B parameter LLM) served locally via Ollama. Built with FastAPI backend, Next.js frontend, and modern vector databases for enterprise-grade document processing.

**📚 Learning Project:** This repository includes comprehensive documentation and visual guides for understanding RAG systems. See [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for educational insights and architecture diagrams.

## 🌟 Features

- **🤖 GPT-OSS:20B Integration** - Open-source 20B parameter model served locally via Ollama (cost-free, private)
- **📊 Financial Document Analysis** - Specialized for financial reports, earnings calls, and market analysis
- **⚡ Modern Tech Stack** - Next.js 14, FastAPI, TypeScript, Python 3.9+
- **🔍 Advanced RAG Pipeline** - LlamaIndex-powered retrieval and generation with GPT-OSS:20B reasoning capabilities
- **📈 Vector Database** - ChromaDB/FAISS for efficient document embeddings
- **🐳 Docker Ready** - Complete containerization for easy deployment
- **🔒 Enterprise Security** - Production-grade security and error handling
- **📝 Comprehensive Testing** - Unit, integration, and end-to-end tests
- **🚀 CI/CD Pipeline** - Automated testing and deployment workflows

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js UI   │    │   FastAPI API   │    │   Ollama        │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   + GPT-OSS:20B │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │ Vector Database │              │
         │              │ (ChromaDB/FAISS)│              │
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                Document Processing Pipeline                  │
│        (PDF, DOCX, TXT, HTML Processing & Chunking)        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** and pip
- **Node.js 18+** and npm
- **Docker** and Docker Compose (optional)
- **Ollama** with GPT-OSS:20B model installed

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/alimpolat/rag-financial-ai-gpt-oss-20b.git
   cd rag-financial-ai-gpt-oss-20b
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Install Ollama and GPT-OSS:20B Model**
   ```bash
   # Install Ollama (https://ollama.com/download)
   # Then install the GPT-OSS:20B model
   ollama pull gpt-oss:20b
   ```

5. **Environment Configuration**
   ```bash
   cp env.example .env
   # Edit .env with your configuration (Ollama URL, etc.)
   ```

6. **Start Services**
   ```bash
   # Terminal 1: Start Ollama (if not running)
   ollama serve

   # Terminal 2: Backend
   cd backend && python -m uvicorn main:app --reload

   # Terminal 3: Frontend
   cd frontend && npm run dev
   ```

6. **Access Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Access application at http://localhost:3000
```

## 📋 Project Structure

```
rag-financial-ai-gpt-oss-20b/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/          # Next.js pages
│   │   ├── lib/            # Utility functions
│   │   └── types/          # TypeScript definitions
│   ├── public/             # Static assets
│   └── package.json        # Frontend dependencies
├── backend/                 # FastAPI backend application
│   ├── api/                # API route handlers
│   ├── core/               # Core configuration
│   ├── services/           # Business logic services
│   ├── models/             # Data models
│   ├── utils/              # Utility functions
│   └── requirements.txt    # Python dependencies
├── models/                 # GPT-OSS model management
├── vector-store/           # Vector database storage
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   ├── deployment/        # Deployment guides
│   └── development/       # Development guides
├── docker/                # Docker configurations
├── tests/                 # Test suites
├── scripts/               # Utility scripts
└── docker-compose.yml     # Multi-service orchestration
```

## 🔧 Technology Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Modern UI components
- **React Query** - Data fetching and caching

### Backend
- **FastAPI** - Modern Python web framework
- **LlamaIndex** - Advanced RAG framework for LLM applications
- **Ollama** - Local LLM serving with GPT-OSS:20B model
- **HuggingFace** - Local sentence transformers for embeddings
- **ChromaDB** - Vector database for embeddings
- **Pydantic** - Data validation and serialization

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-service orchestration
- **GitHub Actions** - CI/CD pipeline
- **Nginx** - Reverse proxy (production)

## 📊 RAG Pipeline

1. **Document Ingestion** - LlamaIndex readers for PDF, DOCX, TXT, HTML, MD files
2. **Text Chunking** - Smart chunking using LlamaIndex SentenceSplitter
3. **Embedding Generation** - Local HuggingFace sentence transformers
4. **Vector Storage** - ChromaDB integration through LlamaIndex vector stores
5. **Query Processing** - LlamaIndex query engines with custom retrievers
6. **Retrieval** - Similarity search with post-processing filters
7. **Generation** - GPT-OSS:20B model via Ollama and LlamaIndex
8. **Response Enhancement** - LlamaIndex response synthesis with advanced reasoning

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=.

# Frontend tests
cd frontend
npm test

# End-to-end tests
npm run test:e2e
```

## 🚀 Deployment

### Production Deployment

1. **Docker Production Build**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build
   ```

2. **Environment Variables**
   - Set production environment variables
   - Configure Ollama URL and model settings
   - Set up vector database connections

3. **SSL/Domain Setup**
   - Configure Nginx for SSL termination
   - Set up domain routing

### Cloud Deployment

- **AWS/GCP/Azure** - Container deployment
- **Kubernetes** - Orchestration for scale
- **Cloud Databases** - Managed vector databases

## 📚 Documentation

### Learning & Architecture
- **[LEARNING_GUIDE.md](LEARNING_GUIDE.md)** - Comprehensive project evaluation with RAG concepts explained (Score: 9/10)
- **[LEARNING_GUIDE.html](LEARNING_GUIDE.html)** - Beautiful browser version with rendered Mermaid diagrams
- **[ARCHITECTURE_VISUAL.md](ARCHITECTURE_VISUAL.md)** - 20+ visual diagrams showing system architecture, data flow, and component interactions
- **[ARCHITECTURE_VISUAL.html](ARCHITECTURE_VISUAL.html)** - Interactive browser version of architecture diagrams

### Development
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code with commands and workflows
- **[.claude/skills/](.claude/skills/)** - Reusable development skills (rag-debug, quick-test, explain-rag)
- [API Documentation](http://localhost:8000/docs) - Auto-generated Swagger UI (when backend running)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [RAG Financial AI (LlamaIndex)](https://github.com/alimpolat/rag-financial-ai-agent-llamapack-llamaindex) - Alternative implementation using LlamaIndex

## 🙏 Acknowledgments

- LlamaIndex team for the excellent RAG framework
- Ollama team for local LLM serving infrastructure
- GPT-OSS:20B model contributors for the open-source LLM
- FastAPI and Next.js communities for modern web frameworks
- ChromaDB team for vector database solutions
- HuggingFace for sentence transformers and embedding models

## 📞 Contact

**Alim Polat** - [LinkedIn](https://se.linkedin.com/in/alimpolat) - Data Scientist

Project Link: [https://github.com/alimpolat/rag-financial-ai-gpt-oss-20b](https://github.com/alimpolat/rag-financial-ai-gpt-oss-20b)

---

⭐ **Star this repository if you find it helpful!**
