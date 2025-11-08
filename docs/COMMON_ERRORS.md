# Common Errors & Solutions

Quick reference for frequent issues encountered during development.

## Azure SDK - Sync vs Async

### Using synchronous Azure SDKs in async frameworks (FastAPI)
```
ReadTimeout: Request timeout after 10 seconds
Event loop blocking / unresponsive application
```

**Problem:** Using synchronous Azure SDKs (`azure.cosmos`, `azure.storage.blob`, `azure.identity`) in async frameworks like FastAPI blocks the event loop, causing timeouts and poor performance.

**Wrong Approach (Don't do this):**
```python
# ❌ BAD: Synchronous SDK + asyncio.to_thread workaround
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import asyncio

async def create_item(item):
    container = get_container()  # sync client
    
    def _create():
        return container.create_item(body=item)
    
    # Thread pool workaround - not recommended
    result = await asyncio.to_thread(_create)
    return result
```

**Correct Approach (Use this):**
```python
# ✅ GOOD: Async SDK with native async/await
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

async def create_item(item):
    async with CosmosClient(endpoint, credential=DefaultAzureCredential()) as client:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        result = await container.create_item(body=item)
        return result
```

**Key Differences:**
- Async SDKs: `azure.cosmos.aio`, `azure.storage.blob.aio`, `azure.identity.aio`
- Use `async with` for context management
- All operations are `await`able
- No need for `asyncio.to_thread` or thread pool executors
- Better performance and resource utilization

**For Blob Storage:**
```python
# ✅ GOOD: Async Blob Storage
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential

async with BlobServiceClient(account_url, credential=DefaultAzureCredential()) as client:
    container = client.get_container_client("mycontainer")
    blob_client = container.get_blob_client("myblob")
    await blob_client.upload_blob(data)
```

**Benefits of Async SDKs:**
1. Native async/await support - no event loop blocking
2. Better connection pooling and resource management
3. Lower overhead (no thread context switching)
4. Official Microsoft-recommended pattern for async frameworks
5. Proper async exception handling

**Important: Async Query Differences**
```python
# ❌ BAD: Using sync-only parameters with async client
items = [item async for item in container.query_items(
    query="SELECT * FROM c",
    enable_cross_partition_query=True  # ← NOT supported in async client!
)]
# Error: TypeError: ClientSession._request() got an unexpected keyword argument 'enable_cross_partition_query'

# ✅ GOOD: Async client handles cross-partition queries automatically
items = [item async for item in container.query_items(
    query="SELECT * FROM c"
    # Cross-partition is automatic - no flag needed!
)]
```

**Key Difference:** Per Microsoft docs: "Unlike the synchronous client, the async client does not have an `enable_cross_partition` flag in the request. Queries without a specified partition key value will attempt to do a cross partition query by default."

**References:**
- [Azure Cosmos DB async examples](https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme?view=azure-python#examples)
- [Azure Cosmos DB async queries](https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme?view=azure-python#queries-with-the-asynchronous-client)
- [Azure Blob Storage async examples](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-python#upload-blobs-asynchronously)
- [Azure Functions async performance](https://learn.microsoft.com/en-us/azure/azure-functions/python-scale-performance-reference#improving-throughput-performance)

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

## GitHub Actions / CI/CD Errors

### ACR login fails with Docker daemon error
```
DOCKER_COMMAND_ERROR
Please verify if Docker client is installed and running
```

**Problem:** Using `az acr login` inside `azure/cli@v2` action fails because the action runs commands in a Docker container that doesn't have access to the Docker daemon on the GitHub runner.

**Wrong Approach (Don't do this):**
```yaml
# ❌ BAD: az acr login in azure/cli action (runs in container)
- name: ACR Login
  uses: azure/cli@v2
  with:
    inlineScript: |
      az acr login --name myacr
# This writes credentials to the container's filesystem,
# but docker/build-push-action runs on the host and can't access them
```

**Correct Approach (Use this):**
```yaml
# ✅ GOOD: az acr login as direct run step (runs on host)
- name: Azure Login
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Log in to Azure Container Registry
  run: |
    az acr login --name ${{ steps.config.outputs.acr_name }}
  # Azure CLI is pre-installed on GitHub runners
  # This runs directly on the host where Docker daemon is available
```

**Why this works:**
- GitHub Ubuntu runners have Azure CLI **pre-installed**
- `azure/login@v2` authenticates the CLI session on the **runner** (not in a container)
- `az acr login` as a `run:` step executes on the **runner** with Docker daemon access
- Credentials are written to `~/.docker/config.json` on the **runner**
- `docker/build-push-action@v6` runs on the **same runner** and reads the credentials

**Key Difference:**
- `azure/cli@v2` action = runs in isolated Docker container (no Docker daemon)
- `run: az acr login` = runs directly on GitHub runner (Docker daemon available)

**When to use each approach:**
- ✅ Use direct `run:` steps for `az acr login` (needs Docker daemon)
- ✅ Use `azure/cli@v2` for Azure management operations that don't need Docker
- ✅ Use `docker/login-action@v3` for non-Azure registries or token-based auth

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

### Shared token cache credential errors
```
CredentialUnavailableError: SharedTokenCacheCredential authentication unavailable
ValueError: Authority validation failed
```
**Problem:** `SharedTokenCacheCredential` can fail on some systems or cause authority validation issues, especially in development environments.

**Fix:** Exclude shared token cache credential when creating `DefaultAzureCredential`:
```python
from azure.identity import DefaultAzureCredential

# ✅ GOOD: Exclude problematic shared token cache
credential = DefaultAzureCredential(
    exclude_shared_token_cache_credential=True
)

# For bearer token providers (Azure OpenAI):
from azure.identity import get_bearer_token_provider
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(exclude_shared_token_cache_credential=True),
    "https://cognitiveservices.azure.com/.default"
)
```

**Why this works:**
- `SharedTokenCacheCredential` attempts to use cached tokens from MSAL, which may not be available or may have authority validation issues
- Excluding it forces fallback to other reliable methods like `AzureCliCredential` or `ManagedIdentityCredential`
- Production environments (managed identity) are unaffected
- Development environments work reliably with `az login` credentials

**When to use:**
- Always in development scripts that use `DefaultAzureCredential`
- Any script that interacts with Azure OpenAI, Storage, Cosmos DB, etc.
- When encountering intermittent authentication errors locally

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