# API Reference

## 1. Security Scheme
All endpoints (unless explicitly public) require `Authorization: Bearer <JWT>` where JWT is issued by Entra ID for the application scope `App.Access` (or carries an approved role).

Validation criteria:
* Issuer: `https://login.microsoftonline.com/{tenant_id}/v2.0`
* Audience: Application ID URI (e.g., `api://<app_id>`)
* Scope (`scp`) includes `App.Access` OR `roles` includes one of declared roles
* Unexpired (`exp`) & not before (`nbf`) within skew window

**Blob Storage Access:**
* Private endpoints with Entra authentication enforced (enterprise policy)
* No SAS tokens or public blob URLs
* Services use managed identity for blob operations
* Images served through service proxy endpoints with streaming responses

Error Responses:
* 401 Unauthorized – missing/invalid token
* 403 Forbidden – token valid but insufficient permission (e.g., ordering for non-owned toy)

## 2. Common Headers
`Authorization: Bearer <token>` – required
`X-Correlation-Id` – optional client-provided trace identifier (UUID)
`Content-Type: multipart/form-data` – required for image upload endpoints

## 3. Endpoints (Skeleton)

### 3.1 Toy Service (`/toy`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /toy | Register new toy | User | `owner_oid` taken from principal; name required |
| GET | /toy/{toy_id} | Get toy detail | User/System | Global read allowed; does not include avatar image data |
| GET | /toy | List all toys | User/System | Pagination required; filterable by owner_oid |
| PATCH | /toy/{toy_id} | Update toy | User | Owner only; partial update |
| DELETE | /toy/{toy_id} | Delete toy | User | Owner only; may fail if dependencies exist |
| POST | /toy/{toy_id}/avatar | Upload avatar image | User | Owner only; multipart/form-data; max 5MB |
| GET | /toy/{toy_id}/avatar | Get avatar image | User/System | Global read; streams image from blob storage |
| DELETE | /toy/{toy_id}/avatar | Delete avatar image | User | Owner only; removes blob reference |

### 3.2 Trip Service (`/trip`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /trip | Create trip for toy | User | Must own toy |
| GET | /trip/{trip_id} | Trip detail | User/System | Global read; includes gallery metadata |
| GET | /trip/{trip_id}/gallery | Gallery listing | User/System | Global read; full gallery images for trip |
| POST | /trip/{trip_id}/gallery | Upload gallery image | User | Owner only; multipart/form-data with landmark info |

### 3.3 Add-On Service (`/addon`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /addon/order | Order accessory/experience | User | Own toy only |
| GET | /addon/{order_id} | Order status | User/System | Owner or system |

### 3.4 Geo Service (`/geo`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /geo/session/start | Start live tracking session | User | Own toy only |
| POST | /geo/session/end | End live tracking session | User | Own toy only |
| GET | /geo/location/{trip_id}/stream (WS) | Live location stream | User | Token validated at connect |

### 3.5 Story Service (`/story`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| GET | /story/{trip_id}/latest | Latest daily story | User/System | Global read |
| POST | /story/{trip_id}/refresh | Request refresh | User/System | System may batch compose |

### 3.6 Agent Service (`/agent`)
(Chat orchestration endpoints – details TBD; inherits same auth scheme.)

### 3.7 Demo Data Init Service (`/demo-data`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /demo-data/import | Import demo data | Admin | Requires `Admin.FullAccess` role; reseeds toy/trip data |
| GET | /health | Health check | Public | No auth required |

**Purpose:** Admin-only service to reseed toy and trip demo content on demand for testing and demonstration purposes.

**Authorization:** Requires Entra ID bearer token with the `Admin.FullAccess` app role. Downstream toy/trip service calls reuse the caller's token for auditing.

**Request Body (POST /demo-data/import):**
```jsonc
{
	"include_toys": true,    // Whether to reseed toy profiles
	"include_trips": true    // Whether to reseed trip itineraries
}
```

**Response (POST /demo-data/import):**
```jsonc
{
	"include_toys": true,
	"include_trips": true,
	"summary": {
		"toys_processed": 5,
		"toy_failures": 0,
		"toy_avatars_uploaded": 5,
		"trips_processed": 10,
		"trip_failures": 0,
		"images_uploaded": 30
	},
	"duration_ms": 2450
}
```

## 4. Standard Error Schema (Draft)
```jsonc
{
	"error": {
		"code": "UNAUTHORIZED | FORBIDDEN | VALIDATION_ERROR | NOT_FOUND",
		"message": "Human readable",
		"correlation_id": "uuid",
		"details": []
	}
}
```

## 5. Versioning & Stability
MVP does not expose explicit API version; prepare to add `/v1/` prefix once stabilization & external consumers arise.

## 6. Rate Limiting (Placeholder)
Applied at APIM for `POST /trip`, `POST /addon/order`, chat endpoints.

## 7. Open Questions
* Story refresh authorization nuances (limit per day?)
* Need for partial gallery field projection for performance.
