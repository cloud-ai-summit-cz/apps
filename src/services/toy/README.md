# Toy Service

Toy Registry & Profiles Service - manages toy profiles with avatar images stored in Cosmos DB and Blob Storage.

## Setup

```powershell
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your Azure resource endpoints (see comments in file)

# Authenticate (for local development)
az login
```

## Running

```powershell
# Start service (http://localhost:8001)
uv run python main.py

# API docs: http://localhost:8001/docs
```

## Testing

```powershell
# Run integration tests (mocked auth + real DB/Blob)
uv run pytest -v

# Tests use dependency override to inject fake auth context
# No JWT token management needed - perfect for CI/CD
```

## API Endpoints

**Toy Management:**
- `POST /toy` - Create (user auth required)
- `GET /toy/{id}` - Read (global)
- `GET /toy` - List with pagination (global)
- `PATCH /toy/{id}` - Update (owner only)
- `DELETE /toy/{id}` - Delete (owner only)

**Avatar Management:**
- `POST /toy/{id}/avatar` - Upload image (owner only, max 5MB)
- `GET /toy/{id}/avatar` - Download (global, cached)
- `DELETE /toy/{id}/avatar` - Remove (owner only)

All endpoints require `Authorization: Bearer <token>` except `/health`.

## Architecture

- **Storage**: Cosmos DB (partition key: toy_id) + Blob Storage (private endpoints)
- **Auth**: Entra ID with owner-based access control
- **Image Handling**: Proxy pattern (no SAS tokens, managed identity only)

See full documentation in repository root `docs/` folder.
