# Story Service Security Notes

Detail the threat model and controls unique to this service. Align with `../../platform/SECURITY.md`.

## Threat Model Snapshot
| Asset | Threat | Mitigation |
| --- | --- | --- |
| Story documents | Unauthorized read/write | Entra JWT on all endpoints; owner scoping enforced via Toy/Trip ownership check; Cosmos RBAC via Managed Identity |
| Story generation pipeline | Prompt injection or model abuse | Input validation, allow-listed context sources (Trip/Toy/Geo only), redact PII before prompt, apply content filters |
| Azure OpenAI access | Credential leakage | Managed Identity with least privilege; no API keys in repo |

## Controls Checklist
- Authentication/Authorization: Bearer JWT validated; reads allowed to authenticated users; mutations (generate/regenerate) require owner or system principal `System.StoryWorker` scope.
- Secrets handling: Managed Identity for Cosmos, Service Bus, and Azure OpenAI; no SAS or shared keys; configuration via `azure.yaml` values.
- Data classification: Stories may contain user-provided text; treat as confidential; never log raw story text.
- Network: Internal-only exposure via gateway; no public blob URLs.

## Testing & Monitoring
- Security tests: ownership enforcement integration tests; negative tests for missing/expired tokens.
- Monitoring: Auth failure metric `auth_failures_total{service="story"}`; alerts on repeated 401/403 spikes.

## Exceptions
- None currently; record deviations with owner and expiry if introduced.