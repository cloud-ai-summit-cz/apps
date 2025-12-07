# Agent Service Deployment Plan

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Pipelines
- CI: lint, unit tests, contract checks; container build; dependency scan.
- CD: ArgoCD sync via `agent-values.yaml`; smoke test `/healthz` and a short chat round-trip.

## Environments
| Environment | Branch/Artifact | Purpose | Approvals |
| --- | --- | --- | --- |
| staging | `main` image tag | Integration with downstream services | Auto |
| production | `release/*` or tag | Public demo | PR + manual |

## Release Steps
1. Preconditions: Cosmos `chat_sessions` container ready; downstream service endpoints configured; Azure OpenAI deployment reachable.
2. Deployment: merge -> build -> values bump -> ArgoCD sync.
3. Verification: run synthetic chat that queries toy/trip and returns location; verify traces and Cosmos write.
4. Rollback: revert values tag; if chat stuck, clear per-session cache.

## Infrastructure
- Cosmos DB container `chat_sessions` (HPK `ownerId`, `sessionId`).
- Optional Service Bus topic `agent-tool-events` if async tools used.
- Azure OpenAI deployment for orchestration.
- AKS Deployment with HPA (CPU 70%, min 2, max 10); consider concurrency limit to protect OpenAI quotas.