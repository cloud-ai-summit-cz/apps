# Testing

## 1. Scope
Defines testing strategy focused on end-to-end integration testing with real Azure resources. Tests validate complete request flows including authentication, authorization, business logic, and Azure service integration (Cosmos DB, Blob Storage).

## 2. Testing Strategy

### Centralized Integration Tests
All tests are located in `src/integration-tests/` and run against actual services with real Azure backends.

**Principles:**
* **No service-level unit tests** - Services contain business logic only, no isolated test suites
* **End-to-end validation** - Tests make real HTTP requests to running services
* **Real Azure resources** - Tests use actual Cosmos DB and Blob Storage (not mocks)
* **Real authentication** - Tests use actual Entra ID tokens from token generation tool
* **Single test suite** - Centralized in `src/integration-tests/` for consistency

### Why This Approach?
1. **Validates complete flows** - Ensures all layers work together (FastAPI, auth, Azure SDKs, Azure resources)
2. **Catches integration issues** - No surprises when deploying to production
3. **Simpler maintenance** - One test suite vs many scattered unit test files
4. **Real-world scenarios** - Tests reflect actual usage patterns with real authentication and data
5. **Azure SDK validation** - Confirms async SDK integration works correctly with real services

## 3. Test Environment Setup

### Prerequisites
* Services running locally (e.g., `cd src/services/toy && uv run python main.py`)
* Azure resources deployed and accessible (Cosmos DB, Blob Storage)
* Valid Entra ID token from `tools/identity/get_auth_token.py`
* `.env` files configured with Azure endpoints and credentials

### Test Execution
```bash
cd src/integration-tests
uv run pytest -v                                    # Run all tests
uv run pytest test_toy_integration.py -v           # Run specific test file
uv run pytest test_toy_integration.py::TestToyServiceAuthentication::test_create_and_get_toy -v  # Run specific test
```

## 4. Test Categories

### Authentication & Authorization Tests
Validates Entra ID JWT token validation and permission enforcement:
* Valid token → Request succeeds
* Missing/invalid token → 401 Unauthorized
* Token without required permissions → 403 Forbidden
* Owner-only operations (update, delete) → 403 for non-owners
* Read operations → Accessible to any authenticated user

### CRUD Operations Tests
Validates core business operations with real data:
* Create toy → Stored in Cosmos DB, returns 201
* Read toy → Retrieved from Cosmos DB, returns 200
* Update toy → Modified in Cosmos DB, returns 200
* Delete toy → Removed from Cosmos DB, returns 204
* List toys → Query from Cosmos DB with pagination

### File Upload Tests
Validates blob storage integration:
* Upload avatar → Stored in Blob Storage, metadata in Cosmos DB
* Download avatar → Retrieved from Blob Storage with correct content type
* Delete avatar → Removed from Blob Storage, metadata cleared

### Ownership Enforcement Tests
Validates authorization rules:
* User can only modify/delete their own toys
* User can read any toy
* Owner field automatically set from JWT token (oid claim)

## 5. Test Infrastructure

### Fixtures (`conftest.py`)
* `service_config`: Service URLs and configuration
* `auth_headers`: Real Entra ID bearer token headers
* `user_oid`: Authenticated user's object ID from token
* `cleanup_toys`: Automatic cleanup of test data after tests

### Test Patterns
```python
def test_create_and_get_toy(service_config, auth_headers, cleanup_toys):
    """Test with real HTTP requests and Azure resources."""
    base_url = service_config["toy_service_url"]
    
    # Create toy (real Cosmos DB write)
    response = httpx.post(
        f"{base_url}/toy",
        json={"name": "Test Toy"},
        headers=auth_headers,
        timeout=10.0
    )
    assert response.status_code == 201
    toy_id = response.json()["id"]
    cleanup_toys.append(toy_id)
    
    # Get toy (real Cosmos DB read)
    response = httpx.get(
        f"{base_url}/toy/{toy_id}",
        headers=auth_headers,
        timeout=10.0
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Toy"
```

## 6. Current Test Coverage

### Toy Service (`test_toy_integration.py`)
**Status:** ✅ All 8 tests passing

Tests:
* `test_create_and_get_toy` - Create and retrieve toy
* `test_authentication_required` - Verify 401 without token
* `test_update_toy` - Modify toy data
* `test_list_toys` - Query and pagination
* `test_delete_toy` - Remove toy and verify deletion
* `test_upload_and_get_avatar` - Upload and retrieve avatar image
* `test_delete_avatar` - Remove avatar from blob storage
* `test_ownership_enforcement` - Verify users can only modify their own toys

**Test Duration:** ~90 seconds (includes real Azure operations)

## 7. Key Technical Details

### Async SDK Integration
Services use async Azure SDKs (`azure.cosmos.aio`, `azure.storage.blob.aio`):
* Native async/await support
* No `enable_cross_partition_query` flag needed (automatic in async client)
* Proper connection pooling and resource cleanup

### Multi-Tenant Authentication
Tests validate correct tenant authentication:
* Uses `DefaultAzureCredential` with `exclude_shared_token_cache_credential=True`
* Ensures correct tenant token (not home tenant) for Azure resource access
* Local dev: Uses Azure CLI credentials
* AKS: Uses Workload Identity / Managed Identity

### Data Cleanup
Tests automatically clean up created resources:
* Cleanup fixture tracks created toy IDs
* Teardown phase deletes all test toys
* Prevents test data accumulation in Azure resources

## 8. Future Enhancements

### Additional Test Scenarios
* Story service integration tests
* Trip service integration tests
* Geo service integration tests
* Cross-service workflow tests (story composition)

### Performance Testing
* Load test target: 1k requests/sec with <100ms P95
* Token validation latency: <5ms P95 (cached JWKS)
* Azure SDK connection pooling efficiency

### Contract Testing
* OpenAPI schema validation
* Error response format consistency
* API versioning compliance

## 9. References

### Related Documentation
* `docs/DESIGN.md` - Architecture and authentication design
* `docs/API_REFERENCE.md` - API endpoint specifications
* `docs/COMMON_ERRORS.md` - Troubleshooting Azure SDK issues
* `docs/IMPLEMENTATION_LOG.md` - Technical implementation decisions

### Azure SDK Documentation
* [Azure Cosmos DB async SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme?view=azure-python#examples)
* [Azure Blob Storage async SDK](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-python#upload-blobs-asynchronously)
* [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
