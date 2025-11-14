# RAG Financial AI - Visual Architecture Guide

> **Purpose**: Comprehensive visual documentation of system architecture using Mermaid diagrams
> **Audience**: Learning and reference
> **Last Updated**: 2025-11-14

---

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [RAG Pipeline Deep Dive](#rag-pipeline-deep-dive)
3. [API Request Flow](#api-request-flow)
4. [Document Processing Pipeline](#document-processing-pipeline)
5. [Database Schema](#database-schema)
6. [Docker Container Architecture](#docker-container-architecture)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Component Dependencies](#component-dependencies)
9. [Authentication Flow](#authentication-flow)
10. [Error Handling Flow](#error-handling-flow)

---

## System Architecture Overview

### High-Level Architecture

```mermaid
C4Context
    title System Context Diagram - RAG Financial AI

    Person(user, "User", "Asks questions about financial documents")

    System(ragApp, "RAG Financial AI", "Document Q&A system using local LLM")

    System_Ext(ollama, "Ollama", "Local LLM server (GPT-OSS:20B)")
    SystemDb_Ext(chromadb, "ChromaDB", "Vector database")
    SystemDb_Ext(redis, "Redis", "Cache layer")

    Rel(user, ragApp, "Uploads docs, asks questions", "HTTPS")
    Rel(ragApp, ollama, "Generates answers", "HTTP")
    Rel(ragApp, chromadb, "Stores/retrieves embeddings", "API")
    Rel(ragApp, redis, "Caches responses", "TCP")
```

### Detailed Component Architecture

```mermaid
graph TB
    subgraph "Client Layer - Port 3000"
        UI[Next.js 14 Frontend]
        COMP[React Components]
        QUERY[React Query Cache]
        API_CLIENT[Axios HTTP Client]

        UI --> COMP
        COMP --> QUERY
        QUERY --> API_CLIENT
    end

    subgraph "API Gateway Layer - Port 8000"
        FASTAPI[FastAPI Application]
        MIDDLEWARE[Middleware Stack]
        ROUTES[API Routes]

        MIDDLEWARE --> |CORS<br/>Security Headers<br/>Rate Limiting| ROUTES
        FASTAPI --> MIDDLEWARE
    end

    subgraph "Authentication & Security"
        JWT[JWT Token Manager]
        AUTH[Auth Service]
        RATE_LIMIT[Rate Limiter]
        FILE_VAL[File Validator]

        ROUTES --> JWT
        JWT --> AUTH
        ROUTES --> RATE_LIMIT
        ROUTES --> FILE_VAL
    end

    subgraph "Business Logic Layer"
        RAG_SVC[RAG Service]
        CHAT_SVC[Chat Service]
        DOC_SVC[Document Service]
        CACHE_SVC[Cache Service]

        AUTH --> RAG_SVC
        AUTH --> CHAT_SVC
        AUTH --> DOC_SVC
    end

    subgraph "AI Processing Layer"
        LLAMAINDEX[LlamaIndex Framework]
        QUERY_ENGINE[Query Engine]
        EMBED[Embedding Generator]
        RETRIEVER[Vector Retriever]

        RAG_SVC --> LLAMAINDEX
        LLAMAINDEX --> QUERY_ENGINE
        LLAMAINDEX --> EMBED
        LLAMAINDEX --> RETRIEVER
    end

    subgraph "Data Access Layer"
        REPO[Repository Pattern]
        VECTOR_STORE[Vector Store Interface]
        CACHE_INTERFACE[Cache Interface]
    end

    subgraph "External Services"
        OLLAMA[Ollama Server<br/>localhost:11434]
        GPT[GPT-OSS:20B Model]

        OLLAMA --> GPT
    end

    subgraph "Data Storage"
        CHROMA[(ChromaDB<br/>Vector Store)]
        REDIS[(Redis Cache<br/>In-Memory)]
        SQLITE[(SQLite<br/>Metadata DB)]
    end

    API_CLIENT -->|HTTP/JSON| FASTAPI

    RAG_SVC --> CACHE_SVC
    CACHE_SVC --> CACHE_INTERFACE
    CACHE_INTERFACE --> REDIS

    DOC_SVC --> REPO
    CHAT_SVC --> REPO
    REPO --> SQLITE

    QUERY_ENGINE --> OLLAMA
    RETRIEVER --> VECTOR_STORE
    VECTOR_STORE --> CHROMA
    EMBED --> CHROMA

    style UI fill:#66bb6a
    style FASTAPI fill:#42a5f5
    style RAG_SVC fill:#ffa726
    style OLLAMA fill:#ff7043
    style CHROMA fill:#ab47bc
    style REDIS fill:#ec407a
```

---

## RAG Pipeline Deep Dive

### Complete RAG Flow (5 Stages)

```mermaid
flowchart TB
    START([User Question]) --> STAGE1

    subgraph STAGE1["Stage 1: Input Processing"]
        direction TB
        Q1[Receive Question]
        Q2[Validate Input]
        Q3[Check Authentication]
        Q4[Apply Rate Limiting]

        Q1 --> Q2 --> Q3 --> Q4
    end

    STAGE1 --> CACHE_CHECK{Check<br/>Cache?}
    CACHE_CHECK -->|Hit| CACHE_RETURN[Return Cached Response]
    CACHE_CHECK -->|Miss| STAGE2

    subgraph STAGE2["Stage 2: Document Check & Embedding"]
        direction TB
        D1[Query ChromaDB Collection Count]
        D2{Has<br/>Documents?}
        D3[Generate Question Embedding]
        D4[Vector: 384 dimensions]

        D1 --> D2
        D2 -->|Yes| D3 --> D4
        D2 -->|No| FALLBACK1[Direct LLM Mode<br/>No RAG]
    end

    STAGE2 --> STAGE3

    subgraph STAGE3["Stage 3: Retrieval"]
        direction TB
        R1[Similarity Search in ChromaDB]
        R2[Calculate Cosine Similarity]
        R3[Retrieve Top-K Chunks<br/>k=10]
        R4[Extract Text + Metadata]
        R5[Calculate Similarity Scores]

        R1 --> R2 --> R3 --> R4 --> R5
    end

    STAGE3 --> STAGE4

    subgraph STAGE4["Stage 4: Generation"]
        direction TB
        G1[Assemble Prompt with Context]
        G2[Send to Ollama API]
        G3[GPT-OSS:20B Processing]
        G4[Stream/Receive Response]
        G5{Request<br/>Successful?}
        G6[Parse Response]

        G1 --> G2 --> G3 --> G4 --> G5
        G5 -->|Yes| G6
        G5 -->|No| FALLBACK2[Fallback Response]
    end

    STAGE4 --> STAGE5

    subgraph STAGE5["Stage 5: Post-Processing"]
        direction TB
        P1[Calculate Confidence Score]
        P2[Format Response with Sources]
        P3[Cache Result]
        P4[Log Query Metrics]
        P5[Return to User]

        P1 --> P2 --> P3 --> P4 --> P5
    end

    CACHE_RETURN --> END
    FALLBACK1 --> STAGE4
    FALLBACK2 --> STAGE5
    STAGE5 --> END([Response Delivered])

    style STAGE1 fill:#e3f2fd
    style STAGE2 fill:#f3e5f5
    style STAGE3 fill:#fff9c4
    style STAGE4 fill:#ffccbc
    style STAGE5 fill:#c8e6c9
    style CACHE_RETURN fill:#80deea
    style FALLBACK1 fill:#ffab91
    style FALLBACK2 fill:#ffab91
```

### Embedding Generation Process

```mermaid
graph TB
    subgraph "Text to Vector Conversion"
        T1["Input Text:<br/>'The company revenue was $2.5M'"]
        T2[Tokenization]
        T3[Token IDs:<br/>[101, 1996, 2194, ...]]
        T4[HuggingFace Model<br/>all-MiniLM-L6-v2]
        T5[Mean Pooling]
        T6["Embedding Vector:<br/>[0.234, -0.456, 0.678, ...]<br/>384 dimensions"]
        T7[L2 Normalization]
        T8["Normalized Vector:<br/>Ready for similarity search"]

        T1 --> T2 --> T3 --> T4 --> T5 --> T6 --> T7 --> T8
    end

    subgraph "Vector Properties"
        P1["Length: Fixed 384 dimensions"]
        P2["Range: -1 to +1 per dimension"]
        P3["Normalized: Unit length"]
        P4["Semantic: Similar meaning = close vectors"]
    end

    style T1 fill:#e1f5ff
    style T8 fill:#c8e6c9
    style T4 fill:#fff3e0
```

### Similarity Search Mechanism

```mermaid
graph LR
    subgraph "Query Vector"
        Q["Question Embedding<br/>[0.23, -0.45, 0.67, ...]"]
    end

    subgraph "Document Vectors in ChromaDB"
        D1["Doc Chunk 1<br/>[0.25, -0.43, 0.69, ...]<br/>Score: 0.92"]
        D2["Doc Chunk 2<br/>[0.10, -0.20, 0.30, ...]<br/>Score: 0.65"]
        D3["Doc Chunk 3<br/>[0.80, 0.50, -0.20, ...]<br/>Score: 0.12"]
        DN["... 100 more chunks"]
    end

    subgraph "Retrieval Process"
        CALC[Cosine Similarity<br/>cos(θ) = A·B / ||A|| ||B||]
        SORT[Sort by Score DESC]
        TOPK[Select Top-10]
    end

    subgraph "Results"
        R["Top-10 Most Similar Chunks<br/>with metadata"]
    end

    Q --> CALC
    D1 --> CALC
    D2 --> CALC
    D3 --> CALC
    DN --> CALC

    CALC --> SORT --> TOPK --> R

    style D1 fill:#4caf50,color:#fff
    style D2 fill:#8bc34a
    style D3 fill:#ffeb3b
    style R fill:#2196f3,color:#fff
```

---

## API Request Flow

### Chat Query Request Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant F as Frontend (Next.js)
    participant RQ as React Query
    participant N as Nginx Proxy
    participant FA as FastAPI Server
    participant MW as Middleware
    participant Auth as Auth Service
    participant RAG as RAG Service
    participant Cache as Redis Cache
    participant Vec as ChromaDB
    participant LLM as Ollama/GPT-OSS

    U->>F: Clicks "Send" with question
    F->>RQ: useMutation(chatApi.query)
    RQ->>F: Set isPending=true

    RQ->>N: POST /api/chat/query<br/>{question, use_cache}
    N->>FA: Forward request
    FA->>MW: Apply middleware stack

    MW->>MW: Check CORS origin
    MW->>MW: Add security headers
    MW->>MW: Check rate limit
    MW-->>FA: Middleware passed ✓

    FA->>Auth: Verify JWT token
    Auth->>Auth: Decode token
    Auth->>Auth: Check expiration
    Auth-->>FA: TokenData (user_id, email)

    FA->>RAG: query(question, user_id)

    RAG->>Cache: get(cache_key)
    Cache-->>RAG: None (cache miss)

    RAG->>Vec: get_collection().count()
    Vec-->>RAG: 150 documents

    RAG->>Vec: similarity_search(question, top_k=10)
    Note over Vec: 1. Embed question<br/>2. Search index<br/>3. Return nearest neighbors
    Vec-->>RAG: 10 chunks + scores

    RAG->>LLM: generate(prompt + context)
    Note over LLM: GPT-OSS:20B processing<br/>Temperature: 0.1<br/>Max tokens: 2048
    LLM-->>RAG: Generated answer

    RAG->>RAG: Calculate confidence from scores
    RAG->>Cache: set(cache_key, response, ttl=300)

    RAG-->>FA: ChatResponse{answer, confidence, sources}
    FA-->>N: HTTP 200 + JSON response
    N-->>RQ: Response data

    RQ->>RQ: onSuccess callback
    RQ->>F: Update state with response
    F->>U: Display answer in chat

    Note over U,LLM: Total latency: 2-5 seconds
```

### Document Upload Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant F as Frontend
    participant FA as FastAPI
    participant Val as File Validator
    participant Proc as Document Processor
    participant LL as LlamaIndex
    participant Emb as Embedding Model
    participant Vec as ChromaDB
    participant DB as SQLite

    U->>F: Drag & drop PDF file
    F->>F: Client-side validation<br/>(size, type, extension)
    F->>FA: POST /api/documents/upload<br/>multipart/form-data

    FA->>Val: validate_file_upload(file)
    Val->>Val: Check file extension
    Val->>Val: Verify MIME type (magic)
    Val->>Val: Scan for malicious patterns
    Val-->>FA: Validation passed ✓

    FA->>Proc: process_document(file_path)

    Proc->>LL: PDFReader().load_data(file)
    LL-->>Proc: List[Document]

    Proc->>LL: SentenceSplitter.split_nodes()
    Note over LL: Chunk size: 1000<br/>Overlap: 200
    LL-->>Proc: List[TextNode] (chunks)

    Proc->>Proc: Add metadata to each node

    loop For each chunk
        Proc->>Emb: encode(chunk_text)
        Emb-->>Proc: Vector[384]
        Proc->>Vec: add(embedding, text, metadata)
    end

    Vec->>Vec: Update vector index
    Vec-->>Proc: Document ID

    Proc->>DB: INSERT INTO documents<br/>(filename, type, chunk_count)
    DB-->>Proc: Document record created

    Proc-->>FA: ProcessingResult{doc_id, chunks}
    FA-->>F: HTTP 201 Created

    F->>U: Show success notification
```

---

## Document Processing Pipeline

### Multi-Format Document Processing

```mermaid
flowchart TB
    START([File Upload]) --> RECEIVE[Receive File]

    RECEIVE --> VAL{Validation}

    VAL -->|Size > 50MB| ERR1[Reject: File too large]
    VAL -->|Invalid Type| ERR2[Reject: Unsupported format]
    VAL -->|Security Risk| ERR3[Reject: Malicious content]
    VAL -->|Valid| DETECT[Detect File Type]

    DETECT --> PDF{.pdf?}
    DETECT --> DOCX{.docx?}
    DETECT --> TXT{.txt?}
    DETECT --> HTML{.html?}
    DETECT --> MD{.md?}

    PDF -->|Yes| READER_PDF[PDFReader<br/>PyPDF2/pdfplumber]
    DOCX -->|Yes| READER_DOCX[DocxReader<br/>python-docx]
    TXT -->|Yes| READER_TXT[FlatReader<br/>utf-8 encoding]
    HTML -->|Yes| READER_HTML[BeautifulSoupWebReader<br/>HTML parsing]
    MD -->|Yes| READER_MD[MarkdownReader<br/>markdown parsing]

    READER_PDF --> EXTRACT[Text Extraction]
    READER_DOCX --> EXTRACT
    READER_TXT --> EXTRACT
    READER_HTML --> EXTRACT
    READER_MD --> EXTRACT

    EXTRACT --> CLEAN[Text Cleaning]
    CLEAN --> |Remove excess whitespace<br/>Normalize characters| CHUNK

    CHUNK[SentenceSplitter]
    CHUNK --> CHUNK_CONFIG["Configuration:<br/>• Size: 1000 chars<br/>• Overlap: 200 chars<br/>• Separator: sentences"]

    CHUNK_CONFIG --> CHUNKS[List of Text Chunks]

    CHUNKS --> META[Add Metadata to Each Chunk]

    META --> META_FIELDS["Metadata Fields:<br/>• filename<br/>• file_type<br/>• chunk_index<br/>• upload_timestamp<br/>• source_page (if PDF)"]

    META_FIELDS --> EMBED_GEN[Generate Embeddings]

    EMBED_GEN --> HF[HuggingFace Model:<br/>all-MiniLM-L6-v2]
    HF --> VECTORS[Vector Embeddings<br/>384-dim per chunk]

    VECTORS --> STORE[Store in ChromaDB]

    STORE --> COLLECTION[ChromaDB Collection]
    COLLECTION --> INDEX[Vector Index Updated]

    INDEX --> LOG_META[Log Metadata to SQLite]
    LOG_META --> SUCCESS([✓ Processing Complete])

    ERR1 --> FAIL([❌ Upload Failed])
    ERR2 --> FAIL
    ERR3 --> FAIL

    style START fill:#e3f2fd
    style SUCCESS fill:#c8e6c9
    style FAIL fill:#ffcdd2
    style CHUNK fill:#fff9c4
    style HF fill:#f3e5f5
    style COLLECTION fill:#e1bee7
```

### Chunking Strategy Visualization

```mermaid
graph TB
    subgraph "Original Document"
        DOC["Financial Report - 10,000 characters<br/>Multiple paragraphs about revenue, expenses, profits"]
    end

    subgraph "Chunk 1 (chars 0-1000)"
        C1["Q4 2024 Financial Results...<br/>Revenue increased to $2.5M...<br/>Costs decreased by 15%..."]
    end

    subgraph "Chunk 2 (chars 800-1800)"
        C2["...Costs decreased by 15%...<br/>Net profit margin improved...<br/>Customer acquisition..."]
    end

    subgraph "Chunk 3 (chars 1600-2600)"
        C3["...Customer acquisition...<br/>Market expansion in APAC...<br/>New product launches..."]
    end

    subgraph "Overlap Regions"
        O1["Overlap 200 chars<br/>Preserves context"]
        O2["Overlap 200 chars<br/>Prevents info loss"]
    end

    DOC --> C1
    DOC --> C2
    DOC --> C3

    C1 -.->|Shared text| O1
    C2 -.->|Shared text| O1
    C2 -.->|Shared text| O2
    C3 -.->|Shared text| O2

    style DOC fill:#e3f2fd
    style C1 fill:#c8e6c9
    style C2 fill:#fff9c4
    style C3 fill:#ffccbc
    style O1 fill:#ffab91
    style O2 fill:#ffab91
```

---

## Database Schema

### ChromaDB Collection Structure

```mermaid
erDiagram
    COLLECTION ||--o{ EMBEDDING : contains
    EMBEDDING ||--|| DOCUMENT_CHUNK : represents
    EMBEDDING ||--|| METADATA : has

    COLLECTION {
        string collection_name PK "rag_documents"
        string embedding_function "HuggingFace"
        int dimension "384"
        string distance_metric "cosine"
        datetime created_at
    }

    EMBEDDING {
        string id PK "UUID"
        float_array vector "384 dimensions"
        datetime created_at
    }

    DOCUMENT_CHUNK {
        string id PK "Same as embedding_id"
        string text "Chunk content"
        int char_count
    }

    METADATA {
        string embedding_id FK
        string filename
        string file_type "pdf|docx|txt|html|md"
        int chunk_index
        datetime upload_timestamp
        string user_id
        int source_page "PDF only"
        string doc_id "Reference to SQLite"
    }
```

### SQLite Metadata Schema

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : uploads
    USERS ||--o{ CHAT_SESSIONS : creates
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : contains
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains

    USERS {
        int id PK
        string email UK
        string username UK
        string hashed_password
        string role "user|admin"
        datetime created_at
        datetime last_login
        boolean is_active
    }

    DOCUMENTS {
        int id PK
        int user_id FK
        string filename
        string file_path
        string file_type
        int file_size_bytes
        string chroma_doc_id
        int total_chunks
        datetime uploaded_at
        string status "processing|completed|failed"
    }

    DOCUMENT_CHUNKS {
        int id PK
        int document_id FK
        string chroma_embedding_id
        int chunk_index
        int char_count
        text preview "First 200 chars"
    }

    CHAT_SESSIONS {
        int id PK
        int user_id FK
        string session_id UK
        datetime created_at
        datetime last_activity
        boolean is_active
    }

    CHAT_MESSAGES {
        int id PK
        int session_id FK
        string role "user|assistant"
        text content
        float confidence "AI responses only"
        json sources "List of doc references"
        datetime timestamp
    }
```

### Redis Cache Structure

```mermaid
graph TB
    subgraph "Redis Key Patterns"
        K1["query_cache:{hash}<br/>TTL: 5 minutes"]
        K2["user_rate_limit:{user_id}<br/>TTL: 1 minute"]
        K3["document_lock:{doc_id}<br/>TTL: 30 seconds"]
        K4["session:{session_id}<br/>TTL: 24 hours"]
    end

    subgraph "Cached Data Structures"
        V1["String: JSON-serialized ChatResponse"]
        V2["Counter: Request count"]
        V3["Boolean: Lock acquired"]
        V4["Hash: Session data"]
    end

    K1 -.-> V1
    K2 -.-> V2
    K3 -.-> V3
    K4 -.-> V4

    style K1 fill:#e1bee7
    style K2 fill:#f48fb1
    style K3 fill:#80cbc4
    style K4 fill:#90caf9
```

---

## Docker Container Architecture

### Container Orchestration

```mermaid
graph TB
    subgraph "Docker Compose Network"
        subgraph "Frontend Container"
            NEXT[Next.js Server<br/>Port 3000]
            NEXT_BUILD[Production Build<br/>Optimized Assets]
            NEXT --> NEXT_BUILD
        end

        subgraph "Backend Container"
            FASTAPI_MAIN[FastAPI Application<br/>Port 8000]
            UVICORN[Uvicorn ASGI Server<br/>4 workers]
            FASTAPI_MAIN --> UVICORN
        end

        subgraph "Nginx Container"
            NGINX[Nginx Reverse Proxy<br/>Port 80/443]
            NGINX_CONF[nginx.conf<br/>Routing Rules]
            SSL[SSL Certificates<br/>Let's Encrypt]
            NGINX --> NGINX_CONF
            NGINX --> SSL
        end

        subgraph "Redis Container"
            REDIS_SRV[Redis Server<br/>Port 6379]
            REDIS_VOL[/data Volume<br/>Persistent Cache]
            REDIS_SRV --> REDIS_VOL
        end

        subgraph "ChromaDB Container"
            CHROMA_SRV[ChromaDB Server<br/>Port 8001]
            CHROMA_VOL[/chroma/data Volume<br/>Vector Store]
            CHROMA_SRV --> CHROMA_VOL
        end

        subgraph "Celery Worker Container"
            CELERY[Celery Worker]
            CELERY_TASKS[Background Tasks<br/>Document Processing]
            CELERY --> CELERY_TASKS
        end
    end

    subgraph "External Dependencies"
        OLLAMA_EXT[Ollama Server<br/>host.docker.internal:11434]
    end

    subgraph "Persistent Volumes"
        VOL1[vector-store/<br/>ChromaDB data]
        VOL2[uploads/<br/>Document storage]
        VOL3[logs/<br/>Application logs]
    end

    NGINX -->|/:3000| NEXT
    NGINX -->|/api:8000| UVICORN

    FASTAPI_MAIN --> REDIS_SRV
    FASTAPI_MAIN --> CHROMA_SRV
    FASTAPI_MAIN --> OLLAMA_EXT

    CELERY --> REDIS_SRV
    CELERY --> CHROMA_SRV

    CHROMA_SRV --> VOL1
    FASTAPI_MAIN --> VOL2
    FASTAPI_MAIN --> VOL3

    style NGINX fill:#4caf50
    style FASTAPI_MAIN fill:#2196f3
    style NEXT fill:#00bcd4
    style REDIS_SRV fill:#f44336
    style CHROMA_SRV fill:#9c27b0
    style OLLAMA_EXT fill:#ff9800
```

### Docker Build Process

```mermaid
flowchart TB
    START([docker-compose up]) --> BUILD_IMAGES

    subgraph "Image Building"
        BUILD_IMAGES[Build Docker Images]
        BUILD_IMAGES --> BUILD_FE[Frontend Image]
        BUILD_IMAGES --> BUILD_BE[Backend Image]

        BUILD_FE --> DEPS_FE[npm install<br/>dependencies]
        DEPS_FE --> NEXT_BUILD[next build<br/>production]
        NEXT_BUILD --> FE_IMAGE[frontend:latest]

        BUILD_BE --> DEPS_BE[pip install -r<br/>requirements.txt]
        DEPS_BE --> BE_IMAGE[backend:latest]
    end

    FE_IMAGE --> NETWORK
    BE_IMAGE --> NETWORK

    subgraph "Network Configuration"
        NETWORK[Create Docker Network<br/>rag-network]
        NETWORK --> ASSIGN_IPS[Assign Internal IPs]
    end

    ASSIGN_IPS --> CREATE_VOLUMES

    subgraph "Volume Creation"
        CREATE_VOLUMES[Create Volumes]
        CREATE_VOLUMES --> V1[vector-store]
        CREATE_VOLUMES --> V2[uploads]
        CREATE_VOLUMES --> V3[redis-data]
    end

    V1 --> START_SERVICES
    V2 --> START_SERVICES
    V3 --> START_SERVICES

    subgraph "Service Startup"
        START_SERVICES[Start Services]
        START_SERVICES --> S1[Redis]
        START_SERVICES --> S2[ChromaDB]
        S1 --> S3[Backend]
        S2 --> S3
        S3 --> S4[Celery]
        S3 --> S5[Nginx]
        S3 --> S6[Frontend]
    end

    S6 --> HEALTH

    subgraph "Health Checks"
        HEALTH[Health Check Loop]
        HEALTH --> H1[Backend: /health]
        HEALTH --> H2[Frontend: /_next/health]
        HEALTH --> H3[Redis: PING]
        HEALTH --> H4[ChromaDB: /api/v1]
    end

    H4 --> READY([System Ready])

    style START fill:#e3f2fd
    style READY fill:#c8e6c9
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```mermaid
flowchart TB
    TRIGGER([Git Push/PR]) --> CHECKOUT

    subgraph "Setup Phase"
        CHECKOUT[Checkout Code]
        CHECKOUT --> CACHE_CHECK{Cache<br/>Exists?}
        CACHE_CHECK -->|Yes| RESTORE[Restore Cache]
        CACHE_CHECK -->|No| INSTALL
        RESTORE --> TEST_JOB
        INSTALL[Install Dependencies] --> TEST_JOB
    end

    subgraph "Test Job - Parallel"
        TEST_JOB[Test Stage]
        TEST_JOB --> PYTEST[pytest backend/<br/>coverage > 70%]
        TEST_JOB --> JEST[Jest frontend/<br/>unit tests]
        TEST_JOB --> LINT_BE[black, isort, flake8]
        TEST_JOB --> LINT_FE[eslint, typescript]

        PYTEST --> COVERAGE[Upload Coverage<br/>to Codecov]
    end

    TEST_JOB --> SEC_CHECK

    subgraph "Security Job - Parallel"
        SEC_CHECK[Security Scan]
        SEC_CHECK --> SAFETY[safety check<br/>Python vulns]
        SEC_CHECK --> NPM_AUDIT[npm audit<br/>Node vulns]
        SEC_CHECK --> TRIVY[Trivy scan<br/>Docker images]
    end

    SEC_CHECK --> INT_TEST

    subgraph "Integration Test Job"
        INT_TEST[Integration Tests]
        INT_TEST --> DOCKER_UP[docker-compose up -d]
        DOCKER_UP --> API_TEST[API endpoint tests]
        API_TEST --> E2E[Playwright E2E tests]
    end

    INT_TEST --> BUILD_CHECK{Tests<br/>Pass?}

    BUILD_CHECK -->|Fail| FAIL_NOTIFY[Send Failure<br/>Notification]
    BUILD_CHECK -->|Pass| BUILD_JOB

    subgraph "Build Job"
        BUILD_JOB[Build Images]
        BUILD_JOB --> BUILD_FE[docker build frontend]
        BUILD_JOB --> BUILD_BE[docker build backend]
        BUILD_FE --> TAG_FE[Tag: latest, sha]
        BUILD_BE --> TAG_BE[Tag: latest, sha]
    end

    TAG_FE --> PUSH
    TAG_BE --> PUSH

    subgraph "Push Job"
        PUSH[Push to Registry]
        PUSH --> GHCR[GitHub Container Registry]
    end

    PUSH --> DEPLOY_CHECK{Branch?}

    DEPLOY_CHECK -->|main| DEPLOY_PROD
    DEPLOY_CHECK -->|develop| DEPLOY_STAGE
    DEPLOY_CHECK -->|feature/*| SKIP_DEPLOY

    subgraph "Deploy Staging"
        DEPLOY_STAGE[Deploy to Staging]
        DEPLOY_STAGE --> STAGE_SSH[SSH to staging server]
        STAGE_SSH --> STAGE_PULL[docker-compose pull]
        STAGE_PULL --> STAGE_UP[docker-compose up -d]
        STAGE_UP --> STAGE_HEALTH[Health check]
    end

    subgraph "Deploy Production"
        DEPLOY_PROD[Deploy to Production]
        DEPLOY_PROD --> PROD_SSH[SSH to prod server]
        PROD_SSH --> PROD_PULL[docker-compose pull]
        PROD_PULL --> PROD_UP[docker-compose up -d]
        PROD_UP --> PROD_HEALTH[Health check]
        PROD_HEALTH --> SMOKE_TEST[Smoke tests]
    end

    STAGE_HEALTH --> SUCCESS_NOTIFY
    SMOKE_TEST --> SUCCESS_NOTIFY
    SKIP_DEPLOY --> END

    SUCCESS_NOTIFY[Send Success<br/>Notification] --> END([Workflow Complete])
    FAIL_NOTIFY --> END

    style TRIGGER fill:#e3f2fd
    style END fill:#c8e6c9
    style FAIL_NOTIFY fill:#ffcdd2
    style SUCCESS_NOTIFY fill:#c8e6c9
```

---

## Component Dependencies

### Backend Dependency Graph

```mermaid
graph TB
    subgraph "Entry Point"
        MAIN[main.py<br/>FastAPI App]
    end

    subgraph "API Layer"
        ROUTES_CHAT[routes/chat.py]
        ROUTES_DOC[routes/documents.py]
        ROUTES_HEALTH[routes/health.py]
    end

    subgraph "Core Layer"
        CONFIG[core/config.py<br/>Settings]
        AUTH[core/auth.py<br/>JWT]
        SECURITY[core/security.py<br/>Validation]
        EXCEPTIONS[core/exceptions.py]
        MIDDLEWARE[core/middleware.py]
    end

    subgraph "Service Layer"
        RAG[services/rag_service.py]
        CHAT[services/chat_service.py]
        DOC[services/document_service.py]
        CACHE[services/cache_service.py]
    end

    subgraph "Utilities"
        DOC_PROC[utils/document_processor.py]
        LOGGER[utils/logger.py]
    end

    subgraph "Repository Layer"
        REPO_USER[repositories/user_repository.py]
        REPO_DOC[repositories/document_repository.py]
        REPO_CHAT[repositories/chat_repository.py]
    end

    subgraph "External Dependencies"
        LLAMAINDEX[LlamaIndex]
        PYDANTIC[Pydantic]
        SQLALCHEMY[SQLAlchemy]
        CHROMADB[ChromaDB Client]
        REDIS_CLIENT[Redis Client]
        REQUESTS[Requests/httpx]
    end

    MAIN --> ROUTES_CHAT
    MAIN --> ROUTES_DOC
    MAIN --> ROUTES_HEALTH
    MAIN --> MIDDLEWARE

    ROUTES_CHAT --> AUTH
    ROUTES_DOC --> AUTH
    ROUTES_CHAT --> RAG
    ROUTES_DOC --> DOC

    RAG --> CACHE
    RAG --> LLAMAINDEX
    RAG --> CONFIG

    DOC --> DOC_PROC
    DOC --> SECURITY
    DOC --> REPO_DOC

    CHAT --> REPO_CHAT

    DOC_PROC --> LLAMAINDEX

    CACHE --> REDIS_CLIENT

    ALL_SERVICES[All Services] --> CONFIG
    ALL_SERVICES --> LOGGER
    ALL_SERVICES --> EXCEPTIONS

    REPO_USER --> SQLALCHEMY
    REPO_DOC --> SQLALCHEMY
    REPO_CHAT --> SQLALCHEMY

    RAG --> CHROMADB
    DOC_PROC --> CHROMADB

    AUTH --> PYDANTIC
    SECURITY --> PYDANTIC

    style MAIN fill:#42a5f5,color:#fff
    style CONFIG fill:#ffa726
    style RAG fill:#66bb6a
```

### Frontend Dependency Graph

```mermaid
graph TB
    subgraph "Entry Point"
        APP[app/page.tsx<br/>Root Page]
        LAYOUT[app/layout.tsx<br/>Root Layout]
    end

    subgraph "Providers"
        QUERY_PROVIDER[lib/query-provider.tsx<br/>React Query]
        THEME_PROVIDER[components/theme-provider.tsx]
    end

    subgraph "Pages"
        CHAT_PAGE[app/chat/page.tsx]
        DOCS_PAGE[app/documents/page.tsx]
    end

    subgraph "Feature Components"
        CHAT_INTERFACE[components/chat/chat-interface.tsx]
        CHAT_MESSAGE[components/chat/chat-message.tsx]
        DOC_UPLOAD[components/documents/document-upload.tsx]
        DOC_LIST[components/documents/document-list.tsx]
    end

    subgraph "UI Components (shadcn)"
        BUTTON[components/ui/button.tsx]
        INPUT[components/ui/input.tsx]
        CARD[components/ui/card.tsx]
        TOAST[components/ui/toast.tsx]
        DIALOG[components/ui/dialog.tsx]
    end

    subgraph "API Layer"
        API_CLIENT[lib/api.ts<br/>Axios Client]
        CHAT_API[lib/api.ts:chatApi]
        DOC_API[lib/api.ts:documentsApi]
    end

    subgraph "Types"
        TYPES[types/index.ts<br/>TypeScript Definitions]
    end

    subgraph "External Dependencies"
        REACT_QUERY[@tanstack/react-query]
        AXIOS[axios]
        RADIX[Radix UI]
        TAILWIND[Tailwind CSS]
        NEXT[Next.js 14]
    end

    LAYOUT --> QUERY_PROVIDER
    LAYOUT --> THEME_PROVIDER
    APP --> CHAT_PAGE
    APP --> DOCS_PAGE

    CHAT_PAGE --> CHAT_INTERFACE
    DOCS_PAGE --> DOC_UPLOAD
    DOCS_PAGE --> DOC_LIST

    CHAT_INTERFACE --> CHAT_MESSAGE
    CHAT_INTERFACE --> BUTTON
    CHAT_INTERFACE --> INPUT
    CHAT_INTERFACE --> TOAST

    DOC_UPLOAD --> BUTTON
    DOC_UPLOAD --> CARD
    DOC_UPLOAD --> TOAST

    CHAT_INTERFACE --> CHAT_API
    DOC_UPLOAD --> DOC_API
    DOC_LIST --> DOC_API

    CHAT_API --> API_CLIENT
    DOC_API --> API_CLIENT

    API_CLIENT --> AXIOS

    ALL_COMPONENTS[All Components] --> TYPES

    QUERY_PROVIDER --> REACT_QUERY
    UI_COMPONENTS[UI Components] --> RADIX
    UI_COMPONENTS --> TAILWIND

    style APP fill:#66bb6a,color:#fff
    style API_CLIENT fill:#42a5f5,color:#fff
    style TYPES fill:#ffa726
```

---

## Authentication Flow

### JWT Authentication Process

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant Auth as Auth Service
    participant DB as SQLite DB
    participant JWT as JWT Handler

    U->>F: Enter credentials<br/>(email, password)
    F->>API: POST /api/auth/login<br/>{email, password}

    API->>Auth: authenticate_user()
    Auth->>DB: SELECT * FROM users<br/>WHERE email = ?
    DB-->>Auth: User record

    Auth->>Auth: verify_password()<br/>bcrypt check

    alt Password Invalid
        Auth-->>API: None
        API-->>F: 401 Unauthorized
        F-->>U: "Invalid credentials"
    end

    Auth-->>API: User object

    API->>JWT: create_access_token(user)
    JWT->>JWT: Encode payload:<br/>{user_id, email, role, exp}
    JWT-->>API: access_token (15 min)

    API->>JWT: create_refresh_token(user)
    JWT->>JWT: Encode payload:<br/>{user_id, exp}
    JWT-->>API: refresh_token (7 days)

    API-->>F: {access_token, refresh_token,<br/>token_type: "bearer"}

    F->>F: Store tokens<br/>localStorage/sessionStorage
    F-->>U: Redirect to dashboard

    Note over U,JWT: Subsequent Requests

    U->>F: Click "Ask Question"
    F->>API: POST /api/chat/query<br/>Authorization: Bearer {token}

    API->>Auth: verify_token(token)
    Auth->>JWT: jwt.decode(token, SECRET_KEY)

    alt Token Expired
        JWT-->>Auth: ExpiredSignatureError
        Auth-->>API: 401 Unauthorized
        API-->>F: Token expired
        F->>F: Try refresh_token
    end

    alt Token Invalid
        JWT-->>Auth: JWTError
        Auth-->>API: 403 Forbidden
        API-->>F: Invalid token
        F-->>U: Redirect to login
    end

    JWT-->>Auth: Decoded payload
    Auth->>DB: Verify user exists & active
    DB-->>Auth: User confirmed
    Auth-->>API: TokenData(user_id, email)

    API->>API: Process request with user context
    API-->>F: Response
    F-->>U: Display result
```

### Role-Based Access Control

```mermaid
graph TB
    REQUEST[Incoming Request] --> EXTRACT_TOKEN[Extract JWT Token]

    EXTRACT_TOKEN --> VERIFY_TOKEN{Token<br/>Valid?}

    VERIFY_TOKEN -->|No| REJECT[401 Unauthorized]
    VERIFY_TOKEN -->|Yes| DECODE[Decode Token Payload]

    DECODE --> GET_ROLE[Extract User Role]

    GET_ROLE --> CHECK_PERMISSION{Required<br/>Permission?}

    CHECK_PERMISSION --> ADMIN_ONLY{Admin Only?}

    ADMIN_ONLY -->|Yes| IS_ADMIN{Role =<br/>admin?}
    IS_ADMIN -->|No| FORBIDDEN[403 Forbidden]
    IS_ADMIN -->|Yes| ALLOW

    ADMIN_ONLY -->|No| AUTH_ONLY{Authenticated<br/>Only?}
    AUTH_ONLY -->|Yes| IS_AUTH{Has Valid<br/>Token?}
    IS_AUTH -->|No| REJECT
    IS_AUTH -->|Yes| ALLOW

    AUTH_ONLY -->|No| ALLOW[✓ Allow Request]

    ALLOW --> EXECUTE[Execute Handler]

    style REQUEST fill:#e3f2fd
    style ALLOW fill:#c8e6c9
    style REJECT fill:#ffcdd2
    style FORBIDDEN fill:#ffcdd2
    style EXECUTE fill:#80deea
```

---

## Error Handling Flow

### Multi-Layer Error Handling

```mermaid
flowchart TB
    START([Request Received]) --> MIDDLEWARE_LAYER

    subgraph "Middleware Layer"
        MIDDLEWARE_LAYER[Security & Rate Limit Checks]
        MIDDLEWARE_LAYER --> MW_ERROR{Error?}
        MW_ERROR -->|CORS Violation| ERR_CORS[403: CORS Error]
        MW_ERROR -->|Rate Limit| ERR_RATE[429: Too Many Requests]
        MW_ERROR -->|None| AUTH_LAYER
    end

    subgraph "Authentication Layer"
        AUTH_LAYER[JWT Verification]
        AUTH_LAYER --> AUTH_ERROR{Error?}
        AUTH_ERROR -->|No Token| ERR_NO_AUTH[401: Authentication Required]
        AUTH_ERROR -->|Invalid Token| ERR_INVALID_AUTH[401: Invalid Token]
        AUTH_ERROR -->|Expired Token| ERR_EXPIRED[401: Token Expired]
        AUTH_ERROR -->|None| SERVICE_LAYER
    end

    subgraph "Service Layer"
        SERVICE_LAYER[Business Logic Execution]
        SERVICE_LAYER --> RAG_EXEC[RAG Query Execution]

        RAG_EXEC --> RAG_ERROR{Error?}

        RAG_ERROR -->|Ollama Down| FALLBACK1[Use Fallback Response]
        RAG_ERROR -->|ChromaDB Error| FALLBACK2[Direct LLM Mode]
        RAG_ERROR -->|No Documents| FALLBACK3[No Documents Response]
        RAG_ERROR -->|None| SUCCESS_RESPONSE

        FALLBACK1 --> GRACEFUL[Graceful Degradation]
        FALLBACK2 --> GRACEFUL
        FALLBACK3 --> GRACEFUL
        GRACEFUL --> WARNING_RESPONSE[200 + Warning Message]
    end

    subgraph "Validation Layer"
        SERVICE_LAYER --> VALIDATION[Input Validation]
        VALIDATION --> VAL_ERROR{Error?}
        VAL_ERROR -->|Invalid Input| ERR_VALIDATION[422: Validation Error]
        VAL_ERROR -->|None| PROCESS
    end

    subgraph "Database Layer"
        PROCESS[Data Access]
        PROCESS --> DB_ERROR{Error?}
        DB_ERROR -->|Connection| ERR_DB[503: Database Unavailable]
        DB_ERROR -->|Integrity| ERR_INTEGRITY[409: Conflict]
        DB_ERROR -->|None| SUCCESS_RESPONSE
    end

    SUCCESS_RESPONSE[✓ Success Response]

    subgraph "Error Responses"
        ERR_CORS --> LOG_ERROR[Log Error]
        ERR_RATE --> LOG_ERROR
        ERR_NO_AUTH --> LOG_ERROR
        ERR_INVALID_AUTH --> LOG_ERROR
        ERR_EXPIRED --> LOG_ERROR
        ERR_VALIDATION --> LOG_ERROR
        ERR_DB --> LOG_ERROR
        ERR_INTEGRITY --> LOG_ERROR

        LOG_ERROR --> FORMAT_ERROR[Format Error Response]
        FORMAT_ERROR --> ERROR_RESPONSE[JSON Error Response]
    end

    WARNING_RESPONSE --> RETURN
    SUCCESS_RESPONSE --> RETURN
    ERROR_RESPONSE --> RETURN

    RETURN([Return to Client])

    style START fill:#e3f2fd
    style SUCCESS_RESPONSE fill:#c8e6c9
    style WARNING_RESPONSE fill:#fff9c4
    style ERROR_RESPONSE fill:#ffcdd2
    style GRACEFUL fill:#80deea
```

### Error Response Format

```mermaid
classDiagram
    class ErrorResponse {
        +string error_type
        +string message
        +dict details
        +int status_code
        +timestamp datetime
        +string request_id
        +toJSON()
    }

    class ValidationError {
        +list field_errors
        +getFieldDetails()
    }

    class AuthenticationError {
        +string token_type
        +string suggested_action
    }

    class ServiceError {
        +string service_name
        +bool is_retryable
        +string fallback_used
    }

    class DatabaseError {
        +string operation
        +string table
        +getSafeMessage()
    }

    ErrorResponse <|-- ValidationError
    ErrorResponse <|-- AuthenticationError
    ErrorResponse <|-- ServiceError
    ErrorResponse <|-- DatabaseError

    note for ErrorResponse "All errors follow consistent format\nfor frontend parsing"
    note for ServiceError "Includes fallback info\nfor graceful degradation"
```

---

## Performance Optimization Flow

### Caching Strategy

```mermaid
graph TB
    QUERY[User Query] --> HASH[Generate Cache Key<br/>SHA256(question + params)]

    HASH --> REDIS_CHECK{Check Redis<br/>Cache}

    REDIS_CHECK -->|Cache Hit| VALIDATE_CACHE{Cache<br/>Valid?}
    VALIDATE_CACHE -->|Yes| RETURN_CACHED[Return Cached Response<br/>~10ms]
    VALIDATE_CACHE -->|No| INVALIDATE[Invalidate Cache]

    REDIS_CHECK -->|Cache Miss| RAG_QUERY[Execute RAG Query]
    INVALIDATE --> RAG_QUERY

    RAG_QUERY --> EMBED[Generate Embedding<br/>~100ms]
    EMBED --> SEARCH[ChromaDB Search<br/>~200ms]
    SEARCH --> LLM[Ollama Generation<br/>~2000ms]

    LLM --> RESPONSE[Format Response]
    RESPONSE --> CACHE_STORE[Store in Redis<br/>TTL: 5 min]
    CACHE_STORE --> RETURN_NEW[Return New Response<br/>~2300ms]

    RETURN_CACHED --> END([Response Delivered])
    RETURN_NEW --> END

    style RETURN_CACHED fill:#4caf50,color:#fff
    style RETURN_NEW fill:#ff9800,color:#fff
    style REDIS_CHECK fill:#e1bee7
```

---

## Summary

This visual architecture guide provides comprehensive diagrams showing:

1. **System Architecture** - How all components connect
2. **RAG Pipeline** - Complete flow from document to answer
3. **API Flows** - Request/response sequences
4. **Data Models** - Database schemas and relationships
5. **Infrastructure** - Docker and deployment architecture
6. **CI/CD** - Automated testing and deployment
7. **Dependencies** - Component relationships
8. **Security** - Authentication and authorization flows
9. **Error Handling** - Multi-layer error management
10. **Performance** - Caching and optimization strategies

These diagrams serve as both **learning resources** and **reference documentation** for understanding how the RAG Financial AI system works at every level.

---

*Generated for educational purposes - 2025-11-14*
