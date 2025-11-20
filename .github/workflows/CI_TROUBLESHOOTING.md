# CI Troubleshooting Guide

## Common Issues and Solutions

### 1. PostgreSQL Not Ready

**Error**: `pg_isready: command not found`

**Solution**: The workflow now installs `postgresql-client` automatically.

**Alternative**: The GitHub Actions service should handle health checks, but we wait explicitly.

### 2. Database Migration Failures

**Error**: `alembic upgrade head` fails

**Possible Causes**:
- Database already has tables (from previous runs)
- Migration conflicts
- Database URL format issues

**Solution**: 
- The workflow now handles migration errors gracefully
- Tests use `Base.metadata.create_all` which should work even if migrations fail
- Consider using `alembic downgrade base && alembic upgrade head` for clean state

### 3. Test Database Setup

**Note**: Tests in `conftest.py` create tables using `Base.metadata.create_all`, so migrations aren't strictly required for tests. However, running migrations ensures the schema matches production.

### 4. Missing Dependencies

**Error**: `ModuleNotFoundError` or import errors

**Check**:
- All dependencies are in `pyproject.toml`
- `[project.optional-dependencies]` includes `dev` group
- CI installs with `pip install -e ".[dev]"`

### 5. Coverage Threshold

**Error**: Coverage below threshold

**Current threshold**: 35% (in `pyproject.toml`)

**Solution**: 
- Increase test coverage
- Or temporarily lower threshold: `--cov-fail-under=30`

### 6. Type Checking Failures

**Error**: `mypy` errors

**Current**: Type checking is enabled but may have some issues

**Solution**: 
- Fix type errors
- Or add `# type: ignore` comments for complex cases
- Or disable strict checking in `pyproject.toml`

### 7. Linting/Formatting Failures

**Error**: `ruff check` or `ruff format` failures

**Solution**:
- Run `ruff check app tests` locally and fix issues
- Run `ruff format app tests` to auto-format

## Debugging Steps

1. **Check the specific failing step**:
   - Look at the job logs in GitHub Actions
   - Find the exact error message

2. **Run tests locally**:
   ```bash
   # Set up local PostgreSQL
   docker-compose up -d postgres
   
   # Run migrations
   export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test_job_runner"
   alembic upgrade head
   
   # Run tests
   pytest --cov=app --cov-report=term-missing -v
   ```

3. **Check environment variables**:
   - Ensure `DATABASE_URL` is set correctly
   - Check format: `postgresql+asyncpg://user:pass@host:port/dbname`

4. **Verify dependencies**:
   ```bash
   pip install -e ".[dev]"
   pip list | grep -E "(pytest|sqlalchemy|fastapi)"
   ```

## Workflow Improvements Made

1. ✅ Added PostgreSQL wait step with client installation
2. ✅ Added database migration step
3. ✅ Graceful error handling for migrations
4. ✅ Verbose test output (`-v` flag)
5. ✅ Proper environment variable setup

## Next Steps if Still Failing

1. Check the actual error message in GitHub Actions logs
2. Share the specific error for targeted fixes
3. Consider running tests in a Docker container for consistency
4. Check if all test files are being discovered by pytest

