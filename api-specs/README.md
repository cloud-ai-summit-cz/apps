# API Specifications

This folder contains the complete OpenAPI specification for the Toy Trip Platform API.

## Files

- **openapi.yaml** - Complete OpenAPI 3.0.3 specification with all endpoints, schemas, and examples

## Viewing the Specification

### Online Viewers
- [Swagger Editor](https://editor.swagger.io/) - Import `openapi.yaml` to view and validate
- [Redoc](https://redocly.github.io/redoc/) - Beautiful API documentation viewer

### Local Development
Install Swagger UI locally:
```powershell
npm install -g swagger-ui-watcher
swagger-ui-watcher openapi.yaml
```

Or use VS Code extension:
- [OpenAPI (Swagger) Editor](https://marketplace.visualstudio.com/items?itemName=42Crunch.vscode-openapi)
- [Swagger Viewer](https://marketplace.visualstudio.com/items?itemName=Arjun.swagger-viewer)

## Validation

Validate the OpenAPI spec:
```powershell
npm install -g @apidevtools/swagger-cli
swagger-cli validate openapi.yaml
```

## Code Generation

Generate client SDKs or server stubs:
```powershell
npm install -g @openapitools/openapi-generator-cli
openapi-generator-cli generate -i openapi.yaml -g python-fastapi -o ../src/services/toy
```

## Current Status

### Implemented
- ✅ Toy Service (complete CRUD)

### Planned
- ⏳ Trip Service
- ⏳ Add-On Service
- ⏳ Geo Service
- ⏳ Story Service
- ⏳ Agent Service

## Maintenance

- Keep in sync with `docs/API_REFERENCE.md` (high-level table format)
- Keep in sync with `docs/DATA_MODELS.md` (data structure definitions)
- Update version in `openapi.yaml` when making breaking changes
- Add examples for all new endpoints
