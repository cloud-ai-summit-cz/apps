# API Specifications

This folder contains OpenAPI specifications for the Toy Trip Platform API, organized per microservice.

## File Structure

### Service Specifications
- **toy-service.yaml** - ✅ Toy Registry & Profiles (implemented)
- **trip-service.yaml** - ⏳ Trip & Gallery Service (planned)
- **addon-service.yaml** - ⏳ Add-On Services (planned)
- **geo-service.yaml** - ⏳ Geo Location & Live Stream (planned)
- **story-service.yaml** - ⏳ Story Composer (planned)
- **agent-service.yaml** - ⏳ AI Agent Service (planned)

### Shared Components
- **_shared.yaml** - Common schemas, security schemes, parameters, and responses

### Legacy
- **openapi.yaml** - Original monolithic specification (deprecated, kept for reference)

## Implementation Status

| Service | Status | Port | Implementation Path |
|---------|--------|------|---------------------|
| Toy Service | ✅ Implemented | 8000 | `src/services/toy/` |
| Trip Service | ⏳ Planned | 8001 | Not yet created |
| Add-On Service | ⏳ Planned | 8002 | Not yet created |
| Geo Service | ⏳ Planned | 8003 | Not yet created |
| Story Service | ⏳ Planned | 8004 | Not yet created |
| Agent Service | ⏳ Planned | 8005 | Not yet created |

## Viewing Specifications

### VS Code Extensions (Recommended)
- [OpenAPI (Swagger) Editor](https://marketplace.visualstudio.com/items?itemName=42Crunch.vscode-openapi)
- [Swagger Viewer](https://marketplace.visualstudio.com/items?itemName=Arjun.swagger-viewer)

### Online Viewers
- [Swagger Editor](https://editor.swagger.io/) - Import individual YAML files to view and validate
- [Redoc](https://redocly.github.io/redoc/) - Beautiful API documentation viewer

### Local Swagger UI
```powershell
# Install globally
npm install -g swagger-ui-watcher

# View specific service
swagger-ui-watcher toy-service.yaml
```

## Validation

### Validate Individual Service
```powershell
npm install -g @apidevtools/swagger-cli

# Validate toy service
swagger-cli validate toy-service.yaml

# Validate all services
Get-ChildItem -Filter "*-service.yaml" | ForEach-Object { swagger-cli validate $_.Name }
```

### Validate Against Implementation
After implementing or modifying a service:
1. Review the service routes (e.g., `src/services/toy/routes/toy_routes.py`)
2. Ensure request/response models match (e.g., `src/services/toy/models/toy.py`)
3. Test all endpoints with the actual implementation
4. Update the spec to reflect any changes

## Code Generation

Generate client SDKs or server stubs for a specific service:
```powershell
npm install -g @openapitools/openapi-generator-cli

# Generate Python FastAPI server stub
openapi-generator-cli generate -i toy-service.yaml -g python-fastapi -o ../src/services/toy-generated

# Generate TypeScript client
openapi-generator-cli generate -i toy-service.yaml -g typescript-axios -o ../src/web/clients/toy
```

## Maintenance Guidelines

### When Implementing a New Service
1. Review the placeholder spec file (e.g., `trip-service.yaml`)
2. Define complete schemas based on `docs/DATA_MODELS.md`
3. Add request/response examples
4. Update the spec as you implement endpoints
5. Validate spec against running service
6. Update this README with implementation status

### When Modifying an Existing Service
1. Update the code first (models, routes)
2. Update the corresponding spec file to match
3. Validate the spec
4. Test all affected endpoints
5. Update `docs/IMPLEMENTATION_LOG.md` with changes

### Sync Requirements
Specs must stay synchronized with:
- **Code:** Service routes and models in `src/services/*/`
- **Design docs:** `docs/DESIGN.md` (architecture decisions)
- **API Reference:** `docs/API_REFERENCE.md` (high-level endpoint table)
- **Data Models:** `docs/DATA_MODELS.md` (entity schemas)

### Versioning
- Increment minor version (e.g., 0.1.0 → 0.2.0) for backwards-compatible changes
- Increment major version (e.g., 0.2.0 → 1.0.0) for breaking changes
- Document breaking changes in `docs/IMPLEMENTATION_LOG.md`

## Testing Endpoints

### Using cURL
```powershell
# Health check
curl http://localhost:8000/health

# Create toy (requires auth token)
curl -X POST http://localhost:8000/toy `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d '{"name":"Teddy","description":"A brave explorer"}'

# List toys
curl http://localhost:8000/toy -H "Authorization: Bearer $token"
```

### Using Postman/Insomnia
Import the spec file into Postman or Insomnia to automatically generate request collections.

## Development Workflow

### Spec-First Development (Recommended)
1. Design API endpoints in the spec file
2. Define schemas and examples
3. Validate spec
4. Generate server stubs (optional)
5. Implement handlers matching the spec
6. Test against the spec

### Code-First Development
1. Implement service endpoints
2. Extract models and routes
3. Update spec to match implementation
4. Validate spec
5. Test for alignment

## Architecture Notes

- Each microservice has its own OpenAPI spec for independent evolution
- Shared components are in `_shared.yaml` for consistency
- Services communicate via REST through API Management (APIM)
- All services use Entra ID JWT authentication
- Private blob storage accessed via service-managed identity (no SAS tokens)
