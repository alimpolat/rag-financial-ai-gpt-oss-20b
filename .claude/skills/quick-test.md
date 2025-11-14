# Quick Test - Fast Test Suite Runner

Run the most important tests quickly for fast feedback during development.

## What This Does

Runs a curated subset of tests focusing on:
- Backend unit tests (core RAG functionality)
- Frontend component tests
- Skips slow integration and E2E tests

## How to Use

Simply ask Claude: "Run quick tests" or "Test my changes"

## What Gets Tested

**Backend Tests:**
- RAG service query logic
- Document processing
- Configuration validation
- Cache service
- Authentication (fast tests only)

**Frontend Tests:**
- Component rendering
- API client functions
- Type checking

**Skipped (for speed):**
- Integration tests with Docker
- E2E browser tests
- Performance/load tests

## Expected Outcome

Fast feedback (typically 30-60 seconds) showing:
- Pass/fail status for each test suite
- Coverage percentage
- Any failing tests with error messages

## When to Use

- ✅ During active development
- ✅ Before committing code
- ✅ Quick validation of changes

## When NOT to Use

- ❌ Before deploying to production (run full test suite)
- ❌ When testing integration between services
- ❌ When testing end-user workflows
