# API Reference

## 1. Security Scheme
All endpoints (unless explicitly public) require `Authorization: Bearer <JWT>` where JWT is issued by Entra ID for the application scope `App.Access` (or carries an approved role).

Validation criteria:
* Issuer: `https://login.microsoftonline.com/{tenant_id}/v2.0`
* Audience: Application ID URI (e.g., `api://<app_id>`)
* Scope (`scp`) includes `App.Access` OR `roles` includes one of declared roles
* Unexpired (`exp`) & not before (`nbf`) within skew window

Error Responses:
* 401 Unauthorized – missing/invalid token
* 403 Forbidden – token valid but insufficient permission (e.g., ordering for non-owned toy)

## 2. Common Headers
`Authorization: Bearer <token>` – required
`X-Correlation-Id` – optional client-provided trace identifier (UUID)

## 3. Endpoints (Skeleton)

### 3.1 Toy Service (`/toy`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /toy | Register new toy | User | `owner_oid` taken from principal |
| GET | /toy/{toy_id} | Get toy detail | User/System | Global read allowed |
| GET | /toy | List all toys | User/System | Pagination required |

### 3.2 Trip Service (`/trip`)
| Method | Path | Description | Auth | Notes |
|--------|------|-------------|------|-------|
| POST | /trip | Create trip for toy | User | Must own toy |
| GET | /trip/{trip_id} | Trip detail incl legs | User/System | Global read |
| GET | /trip/{trip_id}/gallery | Gallery listing | User/System | Global read |

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
