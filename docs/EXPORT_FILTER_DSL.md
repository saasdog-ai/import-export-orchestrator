# Export Filter DSL

The export system includes a safe, flexible filter/query DSL for filtering exported data. Filters are validated against the entity registry to prevent SQL injection.

For the export API endpoints and curl examples, see [EXPORT_API_GUIDE.md](EXPORT_API_GUIDE.md).

## Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{"field": "status", "operator": "eq", "value": "ACTIVE"}` |
| `ne` | Not equal | `{"field": "status", "operator": "ne", "value": "DELETED"}` |
| `lt` | Less than | `{"field": "amount", "operator": "lt", "value": 1000}` |
| `lte` | Less than or equal | `{"field": "amount", "operator": "lte", "value": 1000}` |
| `gt` | Greater than | `{"field": "amount", "operator": "gt", "value": 500}` |
| `gte` | Greater than or equal | `{"field": "amount", "operator": "gte", "value": 500}` |
| `in` | In list | `{"field": "status", "operator": "in", "value": ["ACTIVE", "PENDING"]}` |
| `between` | Between range | `{"field": "amount", "operator": "between", "value": [100, 1000]}` |

### String Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `contains` | Contains substring | `{"field": "name", "operator": "contains", "value": "acme"}` |
| `startswith` | Starts with | `{"field": "name", "operator": "startswith", "value": "A"}` |
| `endswith` | Ends with | `{"field": "email", "operator": "endswith", "value": ".com"}` |
| `ilike` | Case-insensitive like | `{"field": "name", "operator": "ilike", "value": "%acme%"}` |

### Logical Operators

| Operator | Description |
|----------|-------------|
| `and` | All conditions must match |
| `or` | Any condition must match |
| `not` | Negate a condition |

### Relative Dates

| Value | Description |
|-------|-------------|
| `relative:last_7_days` | Last 7 days |
| `relative:last_30_days` | Last 30 days |
| `relative:last_90_days` | Last 90 days |
| `relative:this_month` | Current month |
| `relative:last_month` | Previous month |
| `relative:this_quarter` | Current quarter |
| `relative:this_year` | Current year |

## Examples

### Simple filter

```json
{
  "entity": "bill",
  "fields": ["id", "amount", "date", "vendor.name"],
  "filters": {
    "field": "amount",
    "operator": "gt",
    "value": 1000
  }
}
```

### Compound filter with relative date

```json
{
  "entity": "bill",
  "fields": ["id", "amount", "date", "vendor.name"],
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 1000},
      {"field": "created_at", "operator": "gte", "value": "relative:last_30_days"}
    ]
  },
  "limit": 100
}
```

### Nested field filter (join)

```json
{
  "entity": "bill",
  "fields": ["id", "amount", "vendor.name", "project.code"],
  "filters": {
    "field": "vendor.name",
    "operator": "contains",
    "value": "acme"
  }
}
```

The query engine automatically resolves nested field paths (e.g., `vendor.name`) into SQL JOINs based on the entity's relationship definitions in the registry.

## How It Works

1. The export request is validated against the entity registry — only registered fields and relationships are allowed
2. The query engine builds a SQLAlchemy SELECT with appropriate JOINs from the entity's `RelationshipDef` declarations
3. Filters are translated to `WHERE` clauses using the handler's `get_column()` method for SQL pushdown
4. Relative date values are resolved to naive UTC datetimes at query time
5. Results are serialized via `model_to_dict()` and written to CSV or JSON

## Safety

- All field names are validated against the entity registry — arbitrary column names are rejected
- Filter values are parameterized (never interpolated into SQL)
- The `limit` field caps the result set size
