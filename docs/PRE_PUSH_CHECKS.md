# Pre-Push Checks Guide

This guide explains how to run checks locally before pushing to GitHub to ensure code quality and functionality.

## Quick Start

### Option 1: Use the Pre-Push Hook (Automatic)

The project includes a git pre-push hook that automatically runs checks before pushing:

```bash
# The hook is already configured
# Just try to push - it will run automatically:
git push origin main
```

If checks fail, the push will be blocked. Fix the issues and try again.

### Option 2: Manual Pre-Push Check

Run the pre-push check script manually:

```bash
# Full check (lint, format, type, tests, coverage)
./scripts/pre-push-check.sh

# Or use Make
make pre-push
```

### Option 3: Quick Check (Fast)

For a quick validation before committing:

```bash
./scripts/quick-check.sh

# Or use Make
make check
```

## Available Commands

### Make Commands

```bash
# Run all checks (lint, format, type, tests)
make check

# Pre-push checks (lint, format, tests)
make pre-push

# Individual checks
make lint          # Run linter
make format        # Format code
make mypy          # Type checker
make test          # Run tests
```

### Direct Scripts

```bash
# Full pre-push check
./scripts/pre-push-check.sh

# Quick check (linter + tests only)
./scripts/quick-check.sh
```

## What Gets Checked

### 1. Linter (ruff check)
- Code style violations
- Unused imports
- Syntax errors
- Best practices

**Fix automatically:**
```bash
ruff check --fix app tests
```

### 2. Code Formatting (ruff format)
- Consistent code formatting
- Indentation
- Line length

**Fix automatically:**
```bash
ruff format app tests
```

### 3. Type Checker (mypy)
- Type annotations
- Type errors
- Note: Non-blocking (warnings only)

### 4. Unit Tests (pytest)
- All unit tests must pass
- Tests in `tests/unit/` directory

**Run tests:**
```bash
pytest tests/unit/ -v
```

### 5. Test Coverage
- Shows current test coverage percentage
- Target: 75%+ (currently ~60%)

## Workflow Recommendations

### Before Every Commit

```bash
# Quick check
make check
# or
./scripts/quick-check.sh
```

### Before Pushing to GitHub

```bash
# Full pre-push check
make pre-push
# or
./scripts/pre-push-check.sh
```

### If Checks Fail

1. **Linter errors:**
   ```bash
   ruff check --fix app tests
   ```

2. **Formatting issues:**
   ```bash
   ruff format app tests
   ```

3. **Test failures:**
   ```bash
   pytest tests/unit/ -v
   # Fix failing tests, then re-run
   ```

4. **Type errors (optional):**
   ```bash
   mypy app
   # Fix type annotations
   ```

## Git Hooks Setup

The pre-push hook is automatically configured when you run:

```bash
git config core.hooksPath .githooks
```

This has already been done for this repository. The hook will:
- Run automatically on `git push`
- Block push if checks fail
- Show clear error messages

### Disable Hook (Temporary)

If you need to push without running checks (not recommended):

```bash
git push --no-verify
```

## CI/CD Integration

The same checks run in GitHub Actions:
- `.github/workflows/ci.yml` runs all checks
- Ensures consistency between local and CI

## Troubleshooting

### Hook Not Running

If the pre-push hook doesn't run:

```bash
# Verify hook is configured
git config core.hooksPath

# Should output: .githooks

# If not, set it:
git config core.hooksPath .githooks

# Verify hook exists and is executable
ls -la .githooks/pre-push
```

### Tests Require Database

Unit tests use mocked dependencies, so they don't require a database.

If you see database connection errors:
- Check that you're running unit tests: `pytest tests/unit/`
- Integration tests require a database: `pytest tests/integration/`

### Slow Checks

If checks are too slow:
- Use `./scripts/quick-check.sh` for faster validation
- Skip type checking: `make lint test`
- Run specific test files: `pytest tests/unit/test_specific.py`

## Best Practices

1. **Run checks before committing:**
   ```bash
   make check
   git add .
   git commit -m "Your message"
   ```

2. **Run full check before pushing:**
   ```bash
   make pre-push
   git push
   ```

3. **Fix issues immediately:**
   - Don't push with failing tests
   - Don't push with linting errors
   - Keep code formatted

4. **Use auto-fix when possible:**
   ```bash
   ruff check --fix app tests
   ruff format app tests
   ```

## Summary

✅ **Before commit:** `make check` or `./scripts/quick-check.sh`  
✅ **Before push:** `make pre-push` or `./scripts/pre-push-check.sh`  
✅ **Auto-fix:** `ruff check --fix app tests && ruff format app tests`  
✅ **Git hook:** Automatically runs on `git push`

This ensures your code is always ready for GitHub! 🚀

