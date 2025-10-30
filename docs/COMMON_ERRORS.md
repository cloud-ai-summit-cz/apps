# Common Errors & Solutions

Quick reference for frequent issues encountered during development.

## Pydantic Deprecation Warnings

### `json_encoders` is deprecated
```
PydanticDeprecatedSince20: `json_encoders` is deprecated
```
**Fix:** Replace with `@field_serializer` decorators
```python
# Instead of:
model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda v: v.isoformat()})

# Use:
@field_serializer('id')
def serialize_id(self, value: UUID) -> str:
    return str(value)
```

### `datetime.utcnow()` is deprecated
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```
**Fix:** Use `datetime.now(UTC)`
```python
# Instead of:
datetime.utcnow()

# Use:
from datetime import datetime, UTC
datetime.now(UTC)
```

### Multiple field serializers error
```
PydanticUserError: Multiple field serializer functions were defined for field 'id'
```
**Fix:** Remove duplicate serializers in child classes that inherit from parent models.

### Invalid datetime format in Cosmos DB
```
ValidationError: Input should be a valid datetime, unexpected extra characters
```
**Fix:** Add field validator to handle legacy datetime formats:
```python
@field_validator('created_at', 'updated_at', mode='before')
@classmethod
def parse_datetime(cls, value):
    if isinstance(value, str):
        if value.endswith('+00:00Z'):
            value = value[:-1]  # Remove invalid Z suffix
        elif value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    return value
```

## Azure Cosmos DB Errors

### RBAC permission denied for database creation
```
CosmosAccessForbidden: Request is blocked by Auth
```
**Fix:** Deploy custom Cosmos DB role with database creation permissions:
```bicep
// In cosmosRoleAssignments.bicep
dataActions: [
  'Microsoft.DocumentDB/databaseAccounts/readMetadata'
  'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/*'  // This is required
  'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
  'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
]
```

### Query parameters error
```
TypeError: Session.request() got an unexpected keyword argument 'parameters'
```
**Fix:** Don't pass `parameters=None` to `query_items()`:
```python
# Instead of:
container.query_items(query=query, parameters=None)

# Use conditional:
if parameters:
    container.query_items(query=query, parameters=parameters)
else:
    container.query_items(query=query)
```

## Azure Blob Storage Errors

### Container does not exist
```
ResourceNotFoundError: The specified container does not exist
```
**Fix:** Ensure Bicep provisions blob containers:
```bicep
resource avatarsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'avatars'
  properties: {
    publicAccess: 'None'
  }
}
```

### Cannot create container (RBAC)
```
HttpResponseError: This request is not authorized to perform this operation
```
**Fix:** Remove auto-create logic from code. Containers should be pre-provisioned via Bicep, not created by application code.

## Python Environment Issues

### Module import errors with shared auth
```
ModuleNotFoundError: No module named 'auth'
```
**Fix:** Add path manipulation in service modules:
```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))
from auth import get_auth_context, require_owner
```

### uv vs pip confusion
```
command not found: pip
```
**Fix:** Use `uv` commands consistently:
```bash
uv add pydantic
uv run pytest
uv run uvicorn main:app
```

## Testing Issues

### Tests leave data behind
**Symptom:** Database accumulates test data between runs
**Fix:** Wrap all tests with try/finally cleanup:
```python
def test_something(self, test_client):
    toy_id = None
    try:
        # Test logic
        response = test_client.post("/toy", json=data)
        toy_id = response.json()["id"]
        # Assertions
    finally:
        if toy_id:
            test_client.delete(f"/toy/{toy_id}")
```

### Mock auth not working
```
AttributeError: 'NoneType' object has no attribute 'principal'
```
**Fix:** Override auth dependency properly:
```python
app.dependency_overrides[get_auth_context] = lambda: mock_auth_context
```

### Tests fail intermittently with 500 errors
**Symptom:** Tests pass individually but fail when run together
**Fix:** Ensure proper test isolation and check for resource leaks between tests.

## Configuration Issues

### Environment variables not loaded
**Symptom:** Application uses default values instead of .env settings
**Fix:** Ensure `.env` file is in the correct location relative to where you run the service:
```
src/services/toy/.env  # When running from src/services/toy/
```

### Azure authentication fails
```
DefaultAzureCredential failed to retrieve a token
```
**Fix:** Ensure you're logged in:
```bash
az login
az account show  # Verify correct subscription
```

## Performance Issues

### Memory usage grows during image operations
**Fix:** Use streaming responses for large files:
```python
return StreamingResponse(
    io.BytesIO(blob_data), 
    media_type=content_type,
    headers={"Cache-Control": "public, max-age=3600"}
)
```

### Slow Cosmos DB queries
**Fix:** Ensure proper indexing and partition key usage. Query within single partition when possible.