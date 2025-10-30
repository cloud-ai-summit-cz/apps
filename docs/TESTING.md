# Testing

## 1. Scope
Defines testing strategy for authentication, authorization, and core domain behaviors.

## 2. Layers
| Layer | Purpose | Tooling |
|-------|---------|---------|
| Unit | Pure logic (token parsing, permission checks) | pytest + mocks |
| Integration | FastAPI endpoint auth & permission enforcement | TestClient + signed test JWTs |
| Contract | Ensure API error schema & status codes | JSON schema validation |
| Performance (Auth) | Token validation latency under load | Locust or k6 (future) |

## 3. Authentication Tests
Unit:
* Valid user token → UserPrincipal
* Valid system token → SystemPrincipal
* Missing scope & role → 403 on protected action
* Expired token → 401
* Audience mismatch → 401
* Clock skew (nbf slightly in future) → accepted within ±2m

Integration:
* Order add-on for own toy → 200
* Order add-on for different owner toy → 403
* Read trip detail (any user) → 200
* Start live geo for non-owned toy → 403

## 4. Fixtures & Helpers
* JWKS fixture: provides deterministic keys & rotates kid version.
* Token factory helper: build signed JWTs for user/system.

## 5. Metrics & Observability Validation
Mock or inspect emitted metrics counters after several auth outcomes (success, expired, wrong audience).

## 6. Non-Functional Verification (Future)
Load test target: 1k token validations/sec with <5ms P95 (cached JWKS).

## 7. Open Questions
* Extent of story compose auth tests (system vs user initiation).
* Need for privacy scenario tests if read-all model changes.
