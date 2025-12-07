# Add-On Service Security Notes

Detail the threat model and controls unique to this service. Align with `../../platform/SECURITY.md`.

## Threat Model Snapshot
| Asset | Threat | Mitigation |
| --- | --- | --- |
| Add-on orders | Cross-tenant access or tampering | Entra JWT on all endpoints; owner validation via Trip/Toy; Cosmos RBAC via Managed Identity; idempotency keys to prevent duplicate orders |
| Fulfillment pipeline | Unauthorized gallery updates | Worker uses Managed Identity with scoped permission to Trip Service and Storage; only system scope `System.AddonWorker` allowed |
| Storage assets | Public exposure of fulfillment images | No public URLs; Storage access via Managed Identity; gallery served through Trip Service with auth |

## Controls Checklist
- Authentication/Authorization: Bearer JWT; reads allowed to owner; creates/updates require owner; worker authenticated via system identity.
- Secrets: Managed Identity for Cosmos/Service Bus/Storage; no SAS tokens in logs or config.
- Network: Internal-only API exposure; rate limits on order creation to prevent abuse.
- Data protection: Do not store payment or PII; fulfillment notes sanitized.

## Testing & Monitoring
- Security tests: ownership enforcement on order read/write; worker scope cannot access user endpoints.
- Monitoring: `auth_failures_total{service="addon"}` and spikes in denied fulfillment calls.

## Exceptions
- None known; document if temporary keys are introduced.