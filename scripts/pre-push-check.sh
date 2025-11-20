#!/bin/bash
# Pre-push check script - Run before pushing to GitHub
# This ensures code quality and tests pass before pushing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Pre-Push Checks - Import/Export Orchestrator        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Are you in the project root?${NC}"
    exit 1
fi

FAILED=0

# Step 1: Linter
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1/5: Running linter (ruff check)...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if ruff check app tests; then
    echo -e "${GREEN}✅ Linter passed${NC}"
else
    echo -e "${RED}❌ Linter failed!${NC}"
    echo -e "${YELLOW}💡 Fix with: ruff check --fix app tests${NC}"
    FAILED=1
fi
echo ""

# Step 2: Code Formatting
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 2/5: Checking code formatting...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if ruff format --check app tests; then
    echo -e "${GREEN}✅ Code formatting check passed${NC}"
else
    echo -e "${RED}❌ Code formatting check failed!${NC}"
    echo -e "${YELLOW}💡 Fix with: ruff format app tests${NC}"
    FAILED=1
fi
echo ""

# Step 3: Type Checker
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3/5: Running type checker (mypy)...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if mypy app; then
    echo -e "${GREEN}✅ Type checker passed${NC}"
else
    echo -e "${YELLOW}⚠️  Type checker found issues (non-blocking)${NC}"
    echo -e "${YELLOW}💡 Consider fixing type errors for better code quality${NC}"
    # Don't fail on type errors - they're warnings
fi
echo ""

# Step 4: Unit Tests
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 4/5: Running unit tests...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if pytest tests/unit/ -v --tb=short; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
else
    echo -e "${RED}❌ Unit tests failed!${NC}"
    FAILED=1
fi
echo ""

# Step 5: Test Coverage
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 5/5: Checking test coverage...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
COVERAGE_OUTPUT=$(pytest tests/unit/ --cov=app --cov-report=term-missing -q 2>&1 | tail -1)
if echo "$COVERAGE_OUTPUT" | grep -q "TOTAL"; then
    COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep "TOTAL" | awk '{print $NF}')
    echo -e "${GREEN}✅ Test coverage: ${COVERAGE}${NC}"
else
    echo -e "${YELLOW}⚠️  Could not determine coverage${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${BLUE}║${NC}  ${GREEN}✅ All pre-push checks passed! Ready to push.${NC}  ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${BLUE}║${NC}  ${RED}❌ Pre-push checks failed! Please fix errors.${NC}     ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

