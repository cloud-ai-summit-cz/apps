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

### 2.2 Trip
Represents a trip to a single destination for a toy, tracking gallery images from that destination.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique trip identifier (system-generated) |
| toy_id | string (UUID) | Yes | Reference to the toy taking this trip |
| owner_oid | string | Yes | Entra object ID of the toy owner (denormalized for fast authorization) |
| title | string | Yes | Trip title (max 200 chars) |
| description | string | No | Trip description (max 1000 chars) |
| location_name | string | Yes | Destination city or location (max 200 chars) |
| country_code | string | Yes | ISO 3166-1 alpha-2 country code (uppercase) |
| status | TripStatus | Yes | Overall trip status (planned, in_progress, completed, cancelled) |
| public_tracking_enabled | bool | Yes | Enable public location sharing (default: false) |
| gallery | list[GalleryImage] | Yes | Gallery images from the destination (empty list by default) |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last modification timestamp |

**GalleryImage Model:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image_id | string (UUID) | Yes | Unique image identifier (system-generated) |
| landmark | string | No | Landmark name featured in the image (max 200 chars) |
| blob_name | string | Yes | Internal blob storage reference (e.g., "gallery/{uuid}.jpg") |
| caption | string | No | Optional image caption (max 500 chars) |
| uploaded_at | datetime | Yes | Upload timestamp |
| source | string | Yes | Image source: "user", "addon", or "generated" |

**Validation Rules:**
* `title`: Required, 1-200 characters
* `description`: Optional, max 1000 characters
* `location_name`: Required, represents the single destination for this trip
* `country_code`: Must be valid ISO 3166-1 alpha-2 code (automatically uppercased)
* `toy_id`: Must reference existing toy
* `owner_oid`: Denormalized from toy for fast authorization checks

**Image Handling:**
* **Storage:** Gallery images stored in blob storage `gallery` container
* **Access:** Clients retrieve via `GET /trip/{id}/gallery/{image_id}` endpoint
* **Upload:** Clients upload via `POST /trip/{id}/gallery` with multipart/form-data
* **Security:** Same private endpoint + Entra auth pattern as toy avatars

**Authorization:**
* Create: Toy owner only (validated via toy service inter-service call)
* Read: Global (any authenticated user/system)
* Update/Delete: Toy owner only (validated via owner_oid match)
* Gallery upload: Toy owner only
* Gallery read: Global

**Status Transitions:**
* Trip status can be updated by owner
* Public tracking can be toggled by owner

**Design Rationale:**
* Each trip represents a journey to ONE destination (e.g., Paris, Tokyo, Grand Canyon)
* Gallery images capture the toy's experiences at various landmarks within that destination
* Location tracking is managed through gallery images with landmark metadata
* This simplified model focuses on the core travel experience without complex place management

### 2.3 Add-On Order
Implicitly links to trip and toy; authorization uses trip → toy → owner_oid chain.

## 3. Serialization / Storage
Principal models are not persisted; only `owner_oid` stored with toys. Token claims not stored server-side (stateless validation) except transient logging (structured fields).

## 4. Open Questions
* Need for soft-delete or transfer of toy ownership later? (Impacts `owner_oid` mutability.)
* Additional privacy attributes if global read model evolves.
