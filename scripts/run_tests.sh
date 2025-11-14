#!/bin/bash

# RAG Financial AI - Comprehensive Test Runner
# This script runs all test suites for the project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Parse command line arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-false}

# Display header
echo "========================================="
echo "RAG Financial AI - Test Suite Runner"
echo "========================================="
echo ""

# Function to run backend tests
run_backend_tests() {
    print_status "Running backend tests..."
    cd backend
    
    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Run unit tests
    print_status "Running unit tests..."
    if [ "$COVERAGE" = "true" ]; then
        pytest tests/unit -v --cov=. --cov-report=html --cov-report=term
    else
        pytest tests/unit -v
    fi
    
    # Run integration tests
    print_status "Running integration tests..."
    pytest tests/integration -v
    
    cd ..
}

# Function to run frontend tests
run_frontend_tests() {
    print_status "Running frontend tests..."
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_warning "Installing frontend dependencies..."
        npm install
    fi
    
    # Run Jest tests
    print_status "Running Jest unit tests..."
    if [ "$COVERAGE" = "true" ]; then
        npm test -- --coverage
    else
        npm test
    fi
    
    cd ..
}

# Function to run E2E tests
run_e2e_tests() {
    print_status "Running E2E tests with Playwright..."
    cd frontend
    
    # Install Playwright browsers if needed
    if [ ! -d "node_modules/@playwright" ]; then
        print_warning "Installing Playwright browsers..."
        npx playwright install
    fi
    
    # Ensure services are running
    print_warning "Make sure backend (port 8000) and frontend (port 3000) are running!"
    read -p "Press Enter when services are ready..."
    
    # Run E2E tests
    npm run test:e2e
    
    cd ..
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests with Locust..."
    cd backend/tests/performance
    
    # Install performance test dependencies
    if [ ! -f ".locust_installed" ]; then
        print_warning "Installing Locust dependencies..."
        pip install -r requirements.txt
        touch .locust_installed
    fi
    
    # Ensure backend is running
    print_warning "Make sure backend (port 8000) is running!"
    read -p "Press Enter when backend is ready..."
    
    # Run performance tests
    print_status "Starting Locust performance test (10 users, 30 seconds)..."
    locust -f locustfile.py \
        --host http://localhost:8000 \
        --users 10 \
        --spawn-rate 2 \
        --run-time 30s \
        --headless \
        --html performance_report.html
    
    print_status "Performance report saved to: performance_report.html"
    
    cd ../../..
}

# Function to run linting and type checking
run_code_quality() {
    print_status "Running code quality checks..."
    
    # Backend linting
    print_status "Backend linting..."
    cd backend
    
    if command -v black &> /dev/null; then
        black . --check
    else
        print_warning "Black not installed, skipping Python formatting check"
    fi
    
    if command -v flake8 &> /dev/null; then
        flake8 . --max-line-length=100
    else
        print_warning "Flake8 not installed, skipping Python linting"
    fi
    
    cd ..
    
    # Frontend linting and type checking
    print_status "Frontend linting and type checking..."
    cd frontend
    
    npm run lint
    npm run type-check
    
    cd ..
}

# Main execution
case $TEST_TYPE in
    backend)
        run_backend_tests
        ;;
    frontend)
        run_frontend_tests
        ;;
    e2e)
        run_e2e_tests
        ;;
    performance)
        run_performance_tests
        ;;
    quality)
        run_code_quality
        ;;
    all)
        run_backend_tests
        run_frontend_tests
        run_code_quality
        print_warning "Skipping E2E and performance tests (require running services)"
        print_warning "Run './scripts/run_tests.sh e2e' for E2E tests"
        print_warning "Run './scripts/run_tests.sh performance' for performance tests"
        ;;
    *)
        echo "Usage: $0 [backend|frontend|e2e|performance|quality|all] [coverage]"
        echo ""
        echo "Options:"
        echo "  backend     - Run backend unit and integration tests"
        echo "  frontend    - Run frontend Jest tests"
        echo "  e2e         - Run Playwright E2E tests (requires running services)"
        echo "  performance - Run Locust performance tests (requires running backend)"
        echo "  quality     - Run linting and type checking"
        echo "  all         - Run all tests except E2E and performance"
        echo ""
        echo "Add 'coverage' as second argument to generate coverage reports"
        echo ""
        echo "Examples:"
        echo "  $0 all coverage    # Run all tests with coverage"
        echo "  $0 backend         # Run only backend tests"
        echo "  $0 e2e            # Run E2E tests"
        exit 1
        ;;
esac

print_status "Test execution completed!"
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="

# Generate summary based on what was run
if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "backend" ]; then
    echo "✓ Backend tests completed"
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "frontend" ]; then
    echo "✓ Frontend tests completed"
fi

if [ "$TEST_TYPE" = "e2e" ]; then
    echo "✓ E2E tests completed"
fi

if [ "$TEST_TYPE" = "performance" ]; then
    echo "✓ Performance tests completed"
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "quality" ]; then
    echo "✓ Code quality checks completed"
fi

if [ "$COVERAGE" = "true" ]; then
    echo ""
    print_status "Coverage reports generated!"
    echo "  Backend: backend/htmlcov/index.html"
    echo "  Frontend: frontend/coverage/lcov-report/index.html"
fi

echo ""
echo "========================================="