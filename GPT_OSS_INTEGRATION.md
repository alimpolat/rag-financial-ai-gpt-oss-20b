# GPT-OSS:20B Integration Guide

This guide explains how to set up and use OpenAI's free GPT-OSS:20B model with the RAG Financial AI system.

## 🚀 What is GPT-OSS:20B?

[GPT-OSS:20B](https://ollama.com/library/gpt-oss) is OpenAI's free open-source 20B parameter model designed for:
- **Powerful reasoning** and agentic tasks
- **Function calling** and web browsing capabilities
- **Full chain-of-thought** reasoning process
- **Configurable reasoning effort** (low, medium, high)
- **Fine-tunable** for specific use cases
- **Apache 2.0 license** for commercial use

## 📋 Prerequisites

### System Requirements
- **RAM**: Minimum 16GB (recommended 32GB+)
- **Storage**: 14GB for the model
- **GPU**: Optional but recommended for better performance

### Software Requirements
- [Ollama](https://ollama.com/download) - Local LLM serving
- Python 3.9+ with required packages
- Node.js 18+ (for frontend)

## 🔧 Installation Steps

### 1. Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from [https://ollama.com/download](https://ollama.com/download)

### 2. Install GPT-OSS:20B Model

```bash
# Pull the 20B parameter model
ollama pull gpt-oss:20b

# Verify installation
ollama list
```

### 3. Start Ollama Service

```bash
# Start Ollama in the background
ollama serve

# Or run in foreground (Ctrl+C to stop)
ollama serve
```

### 4. Test the Model

```bash
# Test basic functionality
ollama run gpt-oss:20b "Hello, can you help me analyze financial data?"

# Test with reasoning
ollama run gpt-oss:20b "Let's think step by step about analyzing a company's financial statements."
```

## ⚙️ Configuration

### Environment Variables

Update your `.env` file:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
GPT_OSS_MODEL=gpt-oss:20b
MAX_TOKENS=2048
TEMPERATURE=0.1

# Local Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Model Parameters

The GPT-OSS:20B model supports various parameters:

```python
# In your RAG service
Settings.llm = Ollama(
    model="gpt-oss:20b",
    base_url="http://localhost:11434",
    temperature=0.1,  # 0.0 to 1.0
    request_timeout=120.0,  # Longer timeout for complex reasoning
    # Additional parameters can be passed
)
```

## 🔍 Advanced Features

### 1. Reasoning Effort Configuration

GPT-OSS:20B supports configurable reasoning effort:

```python
# Low effort - faster, less detailed reasoning
# Medium effort - balanced performance
# High effort - slower, more detailed reasoning

# This can be configured in the Ollama model parameters
```

### 2. Function Calling

The model supports native function calling capabilities:

```python
# Example function calling setup
functions = [
    {
        "name": "analyze_financial_ratio",
        "description": "Calculate financial ratios from data",
        "parameters": {
            "type": "object",
            "properties": {
                "ratio_type": {"type": "string", "enum": ["P/E", "ROE", "ROA"]},
                "data": {"type": "object"}
            }
        }
    }
]
```

### 3. Chain-of-Thought Reasoning

Access the model's reasoning process:

```python
# The model will show its thinking process
response = llm.complete(
    "Let's think step by step about this financial analysis..."
)
# Response includes reasoning steps
```

## 🧪 Testing and Validation

### Health Check

The system includes built-in health checks:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check detailed health via API
curl http://localhost:8000/api/v1/health/detailed
```

### Model Performance

Test the model's financial analysis capabilities:

```bash
# Test with sample financial data
ollama run gpt-oss:20b "
Analyze this financial statement:
Revenue: $1,000,000
Expenses: $800,000
Net Income: $200,000

What are the key insights and ratios?
"
```

## 🚀 Performance Optimization

### 1. Memory Management

- **16GB RAM**: Minimum for 20B model
- **32GB+ RAM**: Recommended for optimal performance
- **GPU**: Optional but significantly improves speed

### 2. Batch Processing

For multiple documents:

```python
# Process documents in batches
batch_size = 5
for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]
    # Process batch
```

### 3. Caching

Implement caching for repeated queries:

```python
# Cache embeddings and responses
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text):
    return embed_model.encode(text)
```

## 🔧 Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Restart Ollama
   pkill ollama
   ollama serve
   ```

2. **Model Not Found**
   ```bash
   # List installed models
   ollama list
   
   # Reinstall model
   ollama pull gpt-oss:20b
   ```

3. **Out of Memory**
   ```bash
   # Check available memory
   free -h
   
   # Reduce batch size or use smaller model
   ```

4. **Slow Performance**
   - Ensure sufficient RAM (32GB+ recommended)
   - Use GPU if available
   - Adjust reasoning effort level
   - Implement caching

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Check Ollama logs
ollama logs
```

## 📊 Monitoring

### Health Monitoring

The system provides health endpoints:

- `/api/v1/health` - Basic health check
- `/api/v1/health/detailed` - Detailed status including Ollama

### Performance Metrics

Monitor key metrics:

- Response time
- Memory usage
- Model availability
- Error rates

## 🔗 Resources

- [GPT-OSS Model Card](https://openai.com/index/gpt-oss-model-card/)
- [Ollama Documentation](https://ollama.com/docs)
- [LlamaIndex Ollama Integration](https://docs.llamaindex.ai/en/stable/examples/llm/ollama.html)
- [OpenAI Launch Blog](https://openai.com/index/introducing-gpt-oss)

## 🎯 Next Steps

1. **Fine-tuning**: Customize the model for financial analysis
2. **Function Calling**: Implement financial analysis functions
3. **Multi-modal**: Add support for charts and graphs
4. **Evaluation**: Set up automated testing and evaluation
5. **Deployment**: Scale to production with proper monitoring

This integration provides a powerful, free, and locally-runnable solution for financial document analysis using OpenAI's latest open-source model.
