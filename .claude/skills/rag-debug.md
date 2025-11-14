# RAG Debug - Quick System Health Check

Run a comprehensive health check of your RAG system to identify issues quickly.

## What This Does

Checks all critical components:
- ✅ Ollama service and GPT-OSS:20B model
- ✅ Backend API server
- ✅ ChromaDB vector database
- ✅ Redis cache (optional)
- ✅ End-to-end RAG query test

## How to Use

Simply ask Claude: "Run the RAG debug skill" or "Check system health"

## What Gets Checked

1. **Ollama**: Verifies the LLM service is running and model is loaded
2. **Backend**: Tests FastAPI server connectivity
3. **ChromaDB**: Checks vector database and document count
4. **Redis**: Validates cache connection (optional)
5. **RAG Pipeline**: Runs a test query end-to-end

## Expected Outcome

You'll get a report showing:
- ✅ Green checks for healthy components
- ❌ Red errors with troubleshooting steps
- ⚠️ Warnings for optional components

## Common Issues Detected

- Ollama not running → Solution: `ollama serve`
- Model missing → Solution: `ollama pull gpt-oss:20b`
- No documents uploaded → Solution: Upload test documents
- Backend not responding → Solution: Check logs, restart server
