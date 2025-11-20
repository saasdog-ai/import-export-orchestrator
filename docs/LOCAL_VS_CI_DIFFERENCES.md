# Local vs CI Test Differences

## Why Tests Pass Locally But Fail in GitHub Actions

### Root Cause: SQLAlchemy Model Defaults

The issue was that **SQLAlchemy model defaults** were creating timezone-aware datetimes that bypassed our repository conversion functions.

### The Problem

1. **SQLAlchemy Model Defaults**: When SQLAlchemy creates a new record or updates an existing one, it uses the `default` and `onupdate` lambda functions directly in the model:
   ```python
   created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
   ```
   This creates timezone-aware datetimes that go directly to asyncpg without conversion.

2. **Repository Conversion**: Our repository functions (`_to_naive_utc`) only convert datetimes that are explicitly passed when creating/updating entities. They don't intercept SQLAlchemy's default values.

3. **Local vs CI Differences**:
   - **Local**: Python 3.13.2 might be more lenient or handle the conversion differently
   - **CI**: Python 3.11 with stricter asyncpg behavior throws the error immediately
   - **Database**: Local PostgreSQL might have different timezone settings than CI

### The Fix

We fixed this by ensuring SQLAlchemy model defaults also create **naive UTC datetimes**:

```python
created_at = Column(
    DateTime,
    default=lambda: datetime.now(UTC).replace(tzinfo=None),
    nullable=False,
)
```

This ensures that even when SQLAlchemy uses defaults, the datetimes are naive and compatible with PostgreSQL's `TIMESTAMP WITHOUT TIME ZONE` columns.

### Other Potential Differences

1. **Python Version**:
   - Local: Python 3.13.2
   - CI: Python 3.11
   - **Solution**: Ensure CI uses the same Python version, or test with both

2. **Database Timezone**:
   - Local: Docker Compose sets `TZ: UTC` and `PGTZ: UTC`
   - CI: PostgreSQL service might have different timezone settings
   - **Solution**: Set timezone explicitly in CI workflow

3. **Environment Variables**:
   - Local: May have different environment variables set
   - CI: Clean environment
   - **Solution**: Document all required environment variables

4. **Dependency Versions**:
   - Local: May have different package versions installed
   - CI: Fresh install from `pyproject.toml`
   - **Solution**: Use `pip freeze` to lock versions, or ensure `pyproject.toml` pins versions

### Best Practices to Avoid This

1. **Always test with the same Python version as CI**
2. **Use Docker Compose for local testing** to match production environment
3. **Set explicit timezone in CI workflow**:
   ```yaml
   env:
     TZ: UTC
     PGTZ: UTC
   ```
4. **Ensure model defaults match database column types** (naive for `TIMESTAMP WITHOUT TIME ZONE`)
5. **Test in CI-like environment locally** using Docker

### Verification

To verify the fix works in both environments:

```bash
# Local
pytest tests/unit/test_repositories.py -v

# CI (will run automatically on push)
# Check GitHub Actions logs
```

