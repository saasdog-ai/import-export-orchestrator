# OpenAPI Client Code Generation

This document explains how to access the OpenAPI specification and generate client code for various programming languages.

## OpenAPI Endpoints

The service automatically exposes the OpenAPI 3.1.0 specification through the following endpoints:

### 1. OpenAPI JSON Schema
- **URL**: `http://localhost:8000/openapi.json`
- **Format**: JSON
- **Version**: OpenAPI 3.1.0
- **Description**: Complete OpenAPI specification in JSON format

### 2. Swagger UI (Interactive Documentation)
- **URL**: `http://localhost:8000/docs`
- **Format**: HTML (Interactive UI)
- **Description**: Interactive API documentation where you can test endpoints directly

### 3. ReDoc (Alternative Documentation)
- **URL**: `http://localhost:8000/redoc`
- **Format**: HTML (Documentation UI)
- **Description**: Alternative documentation interface with a clean, readable format

### 4. Root Endpoint (Service Info)
- **URL**: `http://localhost:8000/`
- **Description**: Returns service information including links to all documentation endpoints

## Downloading the OpenAPI Spec

### Using curl
```bash
# Download the OpenAPI JSON spec
curl -o openapi.json http://localhost:8000/openapi.json

# Or with authentication (if required)
curl -H "Authorization: Bearer <your-token>" -o openapi.json http://localhost:8000/openapi.json
```

### Using wget
```bash
wget -O openapi.json http://localhost:8000/openapi.json
```

### Using Python
```python
import requests

response = requests.get("http://localhost:8000/openapi.json")
with open("openapi.json", "w") as f:
    f.write(response.text)
```

## Generating Client Code

### 1. OpenAPI Generator (Recommended)

OpenAPI Generator supports 50+ languages and frameworks.

#### Installation
```bash
# Using Homebrew (macOS)
brew install openapi-generator

# Using npm
npm install @openapi-generator-plus/cli -g

# Using Docker (no installation needed)
docker run --rm openapitools/openapi-generator-cli version
```

#### Generate Client Code

**Python Client:**
```bash
# Download spec first
curl -o openapi.json http://localhost:8000/openapi.json

# Generate Python client
openapi-generator generate \
  -i openapi.json \
  -g python \
  -o ./generated-clients/python \
  --package-name import_export_client \
  --additional-properties=packageVersion=0.1.0

# Or using Docker
docker run --rm \
  -v ${PWD}:/local \
  openapitools/openapi-generator-cli generate \
  -i /local/openapi.json \
  -g python \
  -o /local/generated-clients/python \
  --package-name import_export_client
```

**TypeScript/JavaScript Client:**
```bash
openapi-generator generate \
  -i openapi.json \
  -g typescript-axios \
  -o ./generated-clients/typescript \
  --package-name @your-org/import-export-client
```

**Java Client:**
```bash
openapi-generator generate \
  -i openapi.json \
  -g java \
  -o ./generated-clients/java \
  --package-name com.yourorg.importexport \
  --library okhttp-gson
```

**Go Client:**
```bash
openapi-generator generate \
  -i openapi.json \
  -g go \
  -o ./generated-clients/go \
  --package-name importexport
```

**C# Client:**
```bash
openapi-generator generate \
  -i openapi.json \
  -g csharp \
  -o ./generated-clients/csharp \
  --package-name ImportExportClient
```

### 2. Language-Specific Tools

#### Python: `openapi-python-client`
```bash
pip install openapi-python-client

# Generate Python client
openapi-python-client generate \
  --url http://localhost:8000/openapi.json \
  --output-path ./generated-clients/python
```

#### TypeScript: `openapi-typescript-codegen`
```bash
npm install openapi-typescript-codegen -g

# Generate TypeScript client
openapi-typescript-codegen \
  --input http://localhost:8000/openapi.json \
  --output ./generated-clients/typescript
```

#### Go: `oapi-codegen`
```bash
go install github.com/deepmap/oapi-codegen/cmd/oapi-codegen@latest

# Generate Go client
oapi-codegen \
  -package importexport \
  -generate client \
  openapi.json > ./generated-clients/go/client.go
```

#### Java: `swagger-codegen`
```bash
# Using Maven plugin
mvn org.openapitools:openapi-generator-maven-plugin:generate \
  -DinputSpec=http://localhost:8000/openapi.json \
  -DgeneratorName=java \
  -Doutput=./generated-clients/java
```

### 3. Using Postman

Postman can import OpenAPI specs and generate collections:

1. Open Postman
2. Click **Import**
3. Select **Link** tab
4. Enter: `http://localhost:8000/openapi.json`
5. Click **Continue** → **Import**

Postman will create a collection with all endpoints and example requests.

### 4. Using Insomnia

1. Open Insomnia
2. Click **Create** → **Import/Export** → **Import Data**
3. Select **From URL**
4. Enter: `http://localhost:8000/openapi.json`
5. Click **Import**

## Example: Python Client Usage

After generating a Python client:

```python
from import_export_client import ApiClient, Configuration
from import_export_client.api.jobs_api import JobsApi
from import_export_client.api.exports_api import ExportsApi

# Configure client
configuration = Configuration(
    host="http://localhost:8000",
    access_token="your-jwt-token"  # If authentication is enabled
)

# Create API client
with ApiClient(configuration) as api_client:
    # Use Jobs API
    jobs_api = JobsApi(api_client)
    jobs = jobs_api.get_client_jobs()
    
    # Use Exports API
    exports_api = ExportsApi(api_client)
    export_request = ExportRequest(
        entity="bill",
        fields=["id", "amount", "date"],
        limit=100
    )
    result = exports_api.create_export(export_request)
```

## Example: TypeScript Client Usage

After generating a TypeScript client:

```typescript
import { Configuration, JobsApi, ExportsApi } from '@your-org/import-export-client';

// Configure client
const configuration = new Configuration({
  basePath: 'http://localhost:8000',
  accessToken: 'your-jwt-token' // If authentication is enabled
});

// Use APIs
const jobsApi = new JobsApi(configuration);
const exportsApi = new ExportsApi(configuration);

// Get jobs
const jobs = await jobsApi.getClientJobs();

// Create export
const exportRequest = {
  entity: 'bill',
  fields: ['id', 'amount', 'date'],
  limit: 100
};
const result = await exportsApi.createExport(exportRequest);
```

## Continuous Integration

You can automate client generation in CI/CD:

```yaml
# .github/workflows/generate-clients.yml
name: Generate API Clients

on:
  push:
    branches: [main]
    paths:
      - 'app/api/**'

jobs:
  generate-clients:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start API service
        run: |
          docker-compose up -d
          sleep 10  # Wait for service to start
      
      - name: Download OpenAPI spec
        run: |
          curl -o openapi.json http://localhost:8000/openapi.json
      
      - name: Generate Python client
        uses: openapi-generators/openapi-python-client-action@v1
        with:
          path: openapi.json
          output-path: ./generated-clients/python
      
      - name: Generate TypeScript client
        uses: openapi-generators/openapi-typescript-codegen-action@v1
        with:
          input: openapi.json
          output: ./generated-clients/typescript
      
      - name: Commit generated clients
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add generated-clients/
          git commit -m "Update generated API clients" || exit 0
          git push
```

## Best Practices

1. **Version Control**: Commit generated clients to your repository for reproducibility
2. **Automation**: Generate clients automatically when the API changes
3. **Testing**: Test generated clients against the actual API
4. **Documentation**: Document any customizations or extensions to generated code
5. **Updates**: Regenerate clients when the API schema changes

## Troubleshooting

### OpenAPI 3.1.0 Compatibility

Some older code generators may not fully support OpenAPI 3.1.0. If you encounter issues:

1. **Use OpenAPI Generator 6.0+** (supports OpenAPI 3.1.0)
2. **Convert to OpenAPI 3.0.3** if needed:
   ```bash
   # Using swagger-codegen
   swagger-codegen convert -i openapi.json -l openapi-yaml -o openapi-3.0.yaml
   ```

### Authentication

If your API requires authentication:

1. Include the JWT token in the Authorization header
2. Configure the generated client with authentication:
   ```python
   # Python example
   configuration.access_token = "your-jwt-token"
   ```

### Custom Headers

Some endpoints may require custom headers. Configure them in the generated client:

```python
# Python example
api_client.set_default_header('X-Custom-Header', 'value')
```

## Additional Resources

- [OpenAPI Generator Documentation](https://openapi-generator.tech/docs/generators)
- [OpenAPI Specification](https://swagger.io/specification/)
- [FastAPI OpenAPI Documentation](https://fastapi.tiangolo.com/advanced/openapi-customization/)

