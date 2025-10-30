# Data Models

## 1. Principal Models

### 1.1 Base Principal
Represents an authenticated caller.
| Field | Type | Description |
|-------|------|-------------|
| subject_id | string | Unique identifier (oid for user, appid for system) |
| is_system | bool | True if workload/managed identity |
| roles | list[string] | App roles assigned (e.g., `System.Service`) |
| scopes | list[string] | OAuth scopes (e.g., `App.Access`) |
| issued_at | datetime | Token iat |
| expires_at | datetime | Token exp |

### 1.2 UserPrincipal (extends Base)
| Field | Type | Description |
| oid | string | Entra object id |
| display_name | string | Preferred username or name claim |

### 1.3 SystemPrincipal (extends Base)
| Field | Type | Description |
| app_id | string | Application ID / azp / appid |

### 1.4 AuthContext
| Field | Type | Description |
| principal | Principal | Resolved principal instance |
| raw_claims | dict | Original token claims for audit/troubleshooting |
| token_id | string | Derived from `jti` if present else hash of token header+claims |

## 2. Domain Model Adjustments

### 2.1 Toy
Represents a registered toy that can participate in trips.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique toy identifier (system-generated) |
| owner_oid | string | Yes | Entra object ID of the owner (immutable except ownership transfer - future) |
| name | string | Yes | Display name of the toy (max 100 chars) |
| description | string | No | Toy description/backstory (max 500 chars) |
| avatar_blob_name | string | No | Internal blob storage reference (e.g., "avatars/{uuid}.jpg"); not exposed directly to clients |
| created_at | datetime | Yes | Registration timestamp |
| updated_at | datetime | Yes | Last modification timestamp |

**Validation Rules:**
* `name`: Required, 1-100 characters, trimmed
* `description`: Optional, max 500 characters
* `avatar_blob_name`: Internal reference only; blob storage accessed via managed identity through proxy endpoints
* `owner_oid`: Immutable after creation, used for authorization chain (trip creation, add-ons, geo sessions)

**Image Handling:**
* **Storage:** Avatar images stored in blob storage `avatars` container with private endpoint + Entra auth
* **Access:** Clients retrieve images via `GET /toy/{id}/avatar` endpoint (not direct blob URLs)
* **Upload:** Clients upload via `POST /toy/{id}/avatar` endpoint with multipart/form-data
* **Security:** No SAS tokens or public blob access; service uses managed identity for blob operations

**Authorization:**
* Create: Any authenticated user (becomes owner)
* Read: Global (any authenticated user/system)
* Update/Delete: Owner only (validated via token oid == toy.owner_oid)
* Avatar upload: Owner only
* Avatar read: Global (any authenticated user/system)

### 2.2 Add-On Order
Implicitly links to trip and toy; authorization uses trip → toy → owner_oid chain.

## 3. Serialization / Storage
Principal models are not persisted; only `owner_oid` stored with toys. Token claims not stored server-side (stateless validation) except transient logging (structured fields).

## 4. Open Questions
* Need for soft-delete or transfer of toy ownership later? (Impacts `owner_oid` mutability.)
* Additional privacy attributes if global read model evolves.
