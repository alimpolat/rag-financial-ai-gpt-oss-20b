#!/bin/bash

# RAG Financial AI Setup Script
echo "🚀 Setting up RAG Financial AI project..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_warning "Node.js is not installed. You'll need it for local development."
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_warning "Python 3 is not installed. You'll need it for local development."
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    print_warning "Ollama is not installed. Please install it from https://ollama.com/download"
    print_status "After installing Ollama, run: ollama pull gpt-oss:20b"
else
    print_status "Ollama is installed. Checking for GPT-OSS:20B model..."
    
    # Check if GPT-OSS:20B model is available
    if ollama list | grep -q "gpt-oss"; then
        print_status "GPT-OSS:20B model is already installed"
    else
        print_warning "GPT-OSS:20B model not found. Please run: ollama pull gpt-oss:20b"
    fi
fi

# Create environment file
print_status "Creating environment configuration..."
if [ ! -f .env ]; then
    cp env.example .env
    print_status "Created .env file from template. Please update it with your configurations."
else
    print_warning ".env file already exists. Please check if it needs updates."
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p vector-store/chroma_db
mkdir -p backend/uploads
mkdir -p docker/nginx/ssl

# Set permissions
chmod 755 vector-store
chmod 755 backend/uploads

print_status "✅ Basic setup completed!"

echo ""
echo "📋 Next steps:"
echo "1. Install Ollama from https://ollama.com/download"
echo "2. Install GPT-OSS:20B model: ollama pull gpt-oss:20b"
echo "3. Update .env file with your Ollama configuration"
echo "4. For Docker deployment: docker-compose up --build"
echo "5. For local development:"
echo "   - Start Ollama: ollama serve"
echo "   - Backend: cd backend && pip install -r requirements.txt && python main.py"
echo "   - Frontend: cd frontend && npm install && npm run dev"
echo ""
echo "🌐 Access points:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/docs"
echo "- Ollama API: http://localhost:11434"
echo ""
echo "📚 For more information, check the README.md file."
