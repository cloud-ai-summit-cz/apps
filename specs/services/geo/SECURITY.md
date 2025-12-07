# Geo Service Security Notes

Detail the threat model and controls unique to this service. Align with `../../platform/SECURITY.md`.

## Threat Model Snapshot
| Asset | Threat | Mitigation |
| --- | --- | --- |
| Location data | Unauthorized access to live positions | Entra JWT on REST/WebSocket; ownership validation; Cosmos RBAC via Managed Identity; short TTL to limit exposure |
| Ingestion endpoint | Spoofed or replayed updates | Require auth scopes for simulators; idempotency via `capturedAt` + `tripId`; optional signature on simulator payloads |
| Azure Maps tokens | Key leakage | Prefer Managed Identity where supported; if key required, store in Key Vault and inject as secret ref; never log tokens |

## Controls Checklist
- Authentication/Authorization: Bearer JWT for all endpoints including WebSocket handshake; ingestion allowed for owner or simulator principal with `System.GeoPublisher` scope.
- Secrets: Managed Identity for Cosmos/Service Bus; no SAS URLs; map keys stored outside repo and rotated.
- Network: Service exposed via gateway; no public blob access; rate limiting to defend against abuse.
- Data retention: TTL on location documents; avoid storing precise location beyond necessary window.

## Testing & Monitoring
- Negative tests for cross-owner access; WebSocket connection without token must fail with 401.
- Monitor `auth_failures_total{service="geo"}` and spikes in 403s.

## Exceptions
- None known; document if any simulator bypass is added.