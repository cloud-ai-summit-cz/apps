# Implementation Log

## 2025-10-30 - Authentication & Authorization Baseline
Established design extensions for Entra ID integration, principal models (UserPrincipal/SystemPrincipal), permission matrix (global read, write-own), token validation flow (JWKS caching, scope/role requirements), and testing strategy. Added documentation updates to DESIGN.md, REQUIREMENTS.md, DATA_MODELS.md, API_REFERENCE.md, TESTING.md. Next step: scaffold shared auth module (`src/shared/auth/`).
## 2025-10-30 - Infra Modules: Storage, Cosmos Serverless, RBAC
Added initial Bicep module set for infra provisioning: `storageAccount.bicep`, `cosmosSqlServerless.bicep`, `roleAssignments.bicep`, plus environment orchestrator `main.bicep` and parameters file. Implemented deterministic naming with digit-to-letter transform and centralized RBAC assignment layer (data-plane contributor roles for user principal). Documented deployment & teardown steps in `infra/bicep/README.md`. Future enhancements queued: Private Endpoints, Diagnostic Settings, managed identities expansion.
## 2025-10-30 - Flatten Bicep Module Directory
Refactored module structure by moving all module files directly under `infra/bicep/modules/` (removed nested service subfolders). Updated `main.bicep` paths accordingly. Rationale: simplify discovery, align with single-file module preference, reduce path verbosity. No behavioral changes.
## 2025-10-30 - Naming Logic Moved Into Modules
Adjusted `storageAccount.bicep` and `cosmosSqlServerless.bicep` to internalize resource naming (using `baseNameNoDash` & `baseNameDash` passed from `main.bicep`). Main now only produces base names; modules derive final resource names (`st*`, `cos*`, `db*`, `c*`). Updated outputs to include chosen names. Accepted non-blocking linter warning on role assignment scopes.
## 2025-10-30 - Hardcode SKU & Consistency
Updated storage module to fix SKU at `Standard_ZRS` (removed `skuName` parameter). Updated Cosmos module to hardcode `defaultConsistencyLevel` to `Session` (removed parameter). Simplifies early environment provisioning; parameters can be reintroduced if variability needed.

## 2025-10-30 - Fix Cosmos Data-Plane RBAC
Corrected RBAC implementation after discovering Cosmos DB uses native data-plane role assignments (`Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15`) instead of standard Azure RBAC. Created separate `cosmosRoleAssignments.bicep` module for Cosmos-specific assignments with built-in role ID mapping (`00000000-0000-0000-0000-000000000002` for Data Contributor). Updated `roleAssignments.bicep` to focus solely on Storage (standard `Microsoft.Authorization/roleAssignments`). Modified `main.bicep` to invoke both modules independently.

## 2025-10-30 - Image Handling Architecture: Private Endpoint + Managed Identity Proxy
**Decision:** Enterprise policy enforces private endpoints on blob storage with Entra authentication (no SAS tokens or public access allowed). Implemented proxy pattern for image handling.

**Changes:**
- **DESIGN.md:** Added blob storage section under Data Storage Strategy documenting private endpoint requirement, managed identity access pattern, and service proxy endpoints for avatars/gallery/add-on images. Added streaming & caching considerations.
- **DATA_MODELS.md:** Changed `Toy.avatar_url` → `Toy.avatar_blob_name` (internal blob reference only). Added image handling documentation: upload/download via service endpoints, managed identity for blob operations, authorization rules for avatar CRUD.
- **API_REFERENCE.md:** Added three avatar endpoints: `POST /toy/{id}/avatar` (upload, multipart/form-data, owner only), `GET /toy/{id}/avatar` (download stream, global read), `DELETE /toy/{id}/avatar` (owner only). Updated security scheme to document blob access pattern.
- **openapi.yaml:** Updated `Toy` schema to replace `avatar_url` with `has_avatar` boolean flag. Removed avatar_url from create/update request schemas. Added complete OpenAPI definitions for three avatar endpoints including streaming response specs, Cache-Control headers, and error responses.

**Rationale:** With private endpoints and no SAS tokens, frontend cannot access blob storage directly. Service proxy pattern respects enterprise security policy while maintaining functionality. Services use managed identity for blob access (no credentials in code). Streaming responses prevent memory bloat. Future optimization path: Azure CDN Premium with Private Link origin if performance demands it.

## 2025-10-30 - Toy Service Implementation

**Implemented complete toy service** with Cosmos DB, Blob Storage, and Entra authentication integration.

**Structure:**
- `models/`: Pydantic models (Toy, ToyCreate, ToyUpdate, ToyDocument) with validation
- `repositories/`: ToyRepository with CRUD operations using azure-cosmos SDK + DefaultAzureCredential, auto-creates DB/container
- `services/`: BlobService with upload/download/delete using azure-storage-blob + DefaultAzureCredential, 5MB limit, content-type validation
- `routes/`: Complete REST API (8 endpoints) with auth integration via shared auth module, owner-based access control
- `main.py`: FastAPI app with lifespan management for DB/Blob client initialization/cleanup
- `config.py`: Pydantic Settings for environment configuration
- `pyproject.toml`: uv-based dependency management

**API Endpoints:**
- POST /toy - Create (user auth, auto-assigns owner_oid)
- GET /toy/{id} - Read (global)
- GET /toy - List with pagination/filtering (global)
- PATCH /toy/{id} - Update (owner only)
- DELETE /toy/{id} - Delete (owner only)
- POST /toy/{id}/avatar - Upload image (owner, multipart, max 5MB)
- GET /toy/{id}/avatar - Download image (global, streaming, cached)
- DELETE /toy/{id}/avatar - Remove image (owner only)

**Testing Strategy:**
- **Primary**: Integration tests with mocked auth + real infrastructure (recommended for CI/CD)
  - FastAPI dependency override injects fake AuthContext with test principals
  - Tests execute against real Cosmos DB and Blob Storage
  - No token management needed - fast and reliable
  - Automatic cleanup after each test
- **Optional**: E2E tests with real Entra ID tokens via service principal client credentials flow
  - Documented in README with setup steps (app registration, secret, permissions)
  - For manual validation or secure CI/CD environments only

**Integration Points:**
- Uses shared `auth/` module (dependencies, models, token_validation)
- Path manipulation to import from `src/shared/auth`
- Ownership validation via `require_owner()` helper
- Supports both UserPrincipal and SystemPrincipal (future service-to-service)

**Configuration:**
- All Azure resources via environment variables (tenant, client, endpoints)
- Defaults for database/container names, ports, logging
- Private endpoint enforcement (no public blob access)

**Key Design Decisions:**
- Streaming responses for images (memory efficient)
- Cache-Control headers (1hr) for avatar downloads
- Partition key = toy_id for Cosmos DB locality
- Blob naming: {toy_id}/{uuid}.{ext} for organization
- Auto-initialization of DB/container/blob-container on first access
- Graceful shutdown with resource cleanup in lifespan handler

**Testing Coverage:**
- Create/read/update/delete toy operations
- List with pagination and owner filtering
- Avatar upload/download/delete with real blob operations
- Ownership validation (403 for non-owners)
- Mock auth with multiple test principals

**Next Steps:** Deploy to AKS, configure managed identity, integrate with APIM gateway.

## 2025-10-30 - Simplified Toy Service Documentation

Consolidated README and QUICKSTART into single concise README.md. Removed verbose documentation, kept only essential information: setup, running, testing. Enhanced .env.example with inline comments showing how to get each value. Documentation now follows "just enough to get started" principle.

## 2025-10-30 - Custom Cosmos DB Role for Database Creation

**Problem:** Tests failed with RBAC permission errors. Built-in "Cosmos DB Built-in Data Contributor" role (ID: `00000000-0000-0000-0000-000000000002`) only includes:
- `Microsoft.DocumentDB/databaseAccounts/readMetadata`
- `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*`
- `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*`

Missing `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/*` required for database/container creation.

**Solution:** Created custom Cosmos DB role definition "Cosmos DB Custom Data Owner" in `cosmosRoleAssignments.bicep` with permissions:
- `Microsoft.DocumentDB/databaseAccounts/readMetadata`
- `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/*` (NEW - allows DB creation)
- `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*`
- `Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*`

**Changes:**
- Updated `cosmosRoleAssignments.bicep` to define custom role resource
- Modified role assignment logic to support custom roles
- Changed `main.bicep` to assign custom role instead of built-in Data Contributor
- Removed pytest environment variables from `pyproject.toml` (using `.env` file instead)

**Deployment:** Successfully deployed new role (ID: `6e0272e2-376c-5332-95b2-571d470bc968`) and assigned to user principal.

**Rationale:** Cosmos DB repository auto-creates database/container on first access (infrastructure-as-code for data layer). Requires elevated permissions beyond data-only CRUD operations. Custom role follows least-privilege principle while enabling development workflow.

## 2025-10-30 - Fixed Integration Test Issues

**Problem 1:** Test `test_list_toys` failed with `TypeError: Session.request() got an unexpected keyword argument 'parameters'` when querying Cosmos DB without a filter.

**Root Cause:** In `toy_repository.py`, the `list_all()` method was passing `parameters=None` to `container.query_items()` when no owner filter was specified. The azure-cosmos SDK doesn't accept `None` for the parameters argument - it must be omitted entirely.

**Solution:** Split query execution into conditional branches:
- When `owner_oid` provided: call `query_items()` with `parameters` argument
- Otherwise: call `query_items()` without `parameters` argument

**Problem 2:** Only the last test's toys were being cleaned up, leaving orphaned records in Cosmos DB from other tests.

**Solution:** Wrapped all test methods with try/finally blocks to ensure cleanup happens even if assertions fail. Tracked created `toy_id`s in local variables and deleted them in finally blocks. This guarantees test isolation and prevents data accumulation in the database.

**Changes:**
- `repositories/toy_repository.py`: Fixed `list_all()` to conditionally pass parameters
- `tests/test_toy_integration.py`: Added try/finally cleanup blocks to all 7 test methods

**Result:** All 7 integration tests now pass reliably with proper cleanup.

## 2025-10-30 - Blob Container Infrastructure Setup

**Problem:** Integration tests were passing but avatars weren't being uploaded to blob storage. Investigation revealed the `avatars` container didn't exist, and the service was attempting to auto-create it (which would fail with RBAC permissions).

**Root Cause:** BlobService had logic to create containers if they don't exist (`container.create_container()`), but this requires control-plane permissions that users/managed identities typically don't have. Infrastructure-as-code principle dictates containers should be pre-created via Bicep.

**Solution:**
1. **Added blob container to Bicep** (`storageAccount.bicep`):
   - Created `blobService` resource (parent for containers)
   - Created `avatarsContainer` with `publicAccess: 'None'`
   - Container name: `avatars`

2. **Simplified BlobService** (`blob_service.py`):
   - Removed auto-create logic (`create_container()` call)
   - Service now expects container to exist (fails fast if missing)
   - Simplified initialization: just connects to pre-existing container

**Verification:**
- Deployed updated Bicep successfully
- Re-ran integration tests: all 7 tests pass
- Verified blob operations: `test_upload_and_get_avatar` and `test_delete_avatar` both work
- Checked blob storage: container exists and is empty after tests (proper cleanup)
- Avatar upload → database → download → cleanup cycle fully functional

**Design Principle:** Infrastructure provisioning (containers, databases) belongs in Bicep; application code should assume infrastructure exists. This follows separation of concerns and enables proper RBAC (data-plane only permissions for services).

## 2025-10-30 - API Specs Reorganized per Microservice

**Motivation:** Single monolithic `openapi.yaml` doesn't scale well for microservices architecture. Each service should have independent API specification for autonomous evolution.

**Changes:**
1. **Created service-specific specs:**
   - `toy-service.yaml` - ✅ Complete implementation-verified spec for toy service
   - `trip-service.yaml` - ⏳ Placeholder with planned endpoints
   - `addon-service.yaml` - ⏳ Placeholder with planned endpoints
   - `geo-service.yaml` - ⏳ Placeholder with planned endpoints (WebSocket noted)
   - `story-service.yaml` - ⏳ Placeholder with planned endpoints
   - `agent-service.yaml` - ⏳ Placeholder with planned endpoints

2. **Created shared components:**
   - `_shared.yaml` - Common schemas (ErrorResponse), security schemes (BearerAuth), parameters (CorrelationId, Limit, Offset), responses (401/403/404/422/409)

3. **Validated toy-service.yaml against implementation:**
   - Compared with `src/services/toy/routes/toy_routes.py` (all 8 endpoints match)
   - Verified request/response schemas match `src/services/toy/models/toy.py`
   - Documented actual behavior: owner_oid auto-set from token, streaming responses for images, Cache-Control headers, 5MB upload limit
   - Added `owner_oid` query parameter for list endpoint (filter by owner)
   - Included detailed examples for all operations

4. **Updated README.md:**
   - Documented new multi-file structure
   - Added implementation status table with ports
   - Expanded validation, code generation, testing sections
   - Added maintenance guidelines: when to update specs, sync requirements, versioning rules
   - Documented spec-first vs code-first workflows
   - Noted legacy `openapi.yaml` as deprecated reference

**Architecture Benefits:**
- **Independent evolution:** Each microservice can version and evolve its API independently
- **Clear ownership:** Service teams own their specs
- **Reduced conflicts:** No merge conflicts on single monolithic spec file
- **Better navigation:** Easy to find relevant endpoints per service
- **Code generation:** Generate service-specific clients/stubs

**Design Decision:** Used `_shared.yaml` prefix (underscore) to distinguish shared components from service specs. Services can reference shared components if needed (though currently self-contained for simplicity).

**Next Steps:** As other services are implemented, complete their placeholder specs with full schemas, examples, and validation against actual code.

## 2025-10-30 - Fixed Pydantic Deprecation Warnings

**Problem:** Tests were showing multiple deprecation warnings from Pydantic v2.x:
1. **`json_encoders` deprecation:** Warning that `json_encoders` config option is deprecated in favor of custom field serializers
2. **`datetime.utcnow()` deprecation:** Python 3.12+ deprecated `datetime.utcnow()` in favor of `datetime.now(UTC)`

**Root Cause Analysis:**
- **json_encoders issue:** `models/toy.py` was using deprecated `ConfigDict(json_encoders={UUID: str, datetime: lambda v: v.isoformat() + "Z"})` syntax
- **datetime.utcnow() issue:** Both `models/toy.py` default factories and `repositories/toy_repository.py` update logic were using deprecated `datetime.utcnow()`
- **Datetime serialization conflict:** Field serializers were creating invalid ISO format strings like `"2025-10-30T13:57:53.397544+00:00Z"` (both timezone offset AND Z suffix)

**Solution:**
1. **Replaced json_encoders with field_serializer decorators:**
   ```python
   @field_serializer('id')
   def serialize_id(self, value: UUID) -> str:
       return str(value)
   
   @field_serializer('created_at', 'updated_at')
   def serialize_datetime(self, value: datetime) -> str:
       return value.isoformat() if value else None
   ```

2. **Updated datetime creation to use UTC:**
   ```python
   # In models: 
   created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
   
   # In repository:
   item["updated_at"] = datetime.now(UTC).isoformat()
   ```

3. **Added field validator for backward compatibility:**
   ```python
   @field_validator('created_at', 'updated_at', mode='before')
   @classmethod
   def parse_datetime(cls, value):
       """Handle various datetime formats from Cosmos DB including legacy Z-suffix formats."""
       if isinstance(value, str):
           if value.endswith('+00:00Z'):
               value = value[:-1]  # Remove invalid Z suffix
           elif value.endswith('Z'):
               value = value[:-1] + '+00:00'
           return datetime.fromisoformat(value)
       return value
   ```

4. **Fixed ToyDocument serializer conflicts:**
   - Removed duplicate serializers for inherited fields
   - Only `toy_id` gets custom serialization in child class
   - Parent datetime serializers handle `created_at`/`updated_at`

5. **Updated ToyDocument.from_toy() method:**
   - Avoid `model_dump()` which triggers serialization
   - Extract fields directly to preserve datetime objects
   - Prevents serialization → deserialization round-trip issues

**Testing Results:**
- ✅ All 7 integration tests pass
- ✅ No deprecation warnings in test output
- ✅ Datetime handling works correctly for create/read/update operations
- ✅ Backward compatibility with existing data in Cosmos DB
- ✅ Field serializers properly format output for JSON responses

**Technical Details:**
- **Before:** `datetime.utcnow()` → deprecated, `json_encoders` → deprecated
- **After:** `datetime.now(UTC)` → modern Python 3.12+, `@field_serializer` → Pydantic v2 best practice
- **Format change:** Removed invalid `+00:00Z` format, now uses standard `+00:00` timezone offset
- **Compatibility:** Field validator handles legacy data with Z suffixes

**Impact:** Eliminated all deprecation warnings while maintaining full functionality and backward compatibility. Code now follows modern Python and Pydantic best practices.