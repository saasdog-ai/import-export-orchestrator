#!/bin/bash
# Quick check script - Fast validation before committing/pushing
# Runs only essential checks (linter and tests)

set -e

echo "🔍 Running quick checks..."
echo ""

# Linter
echo "1. Linter..."
if ! ruff check app tests; then
    echo "❌ Linter failed! Run: ruff check --fix app tests"
    exit 1
fi
echo "✅ Linter passed"
echo ""

# Tests
echo "2. Unit tests..."
if ! pytest tests/unit/ -v --tb=line -q; then
    echo "❌ Tests failed!"
    exit 1
fi
echo "✅ Tests passed"
echo ""

echo "✅ Quick checks passed!"
exit 0

