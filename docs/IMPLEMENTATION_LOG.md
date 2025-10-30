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
