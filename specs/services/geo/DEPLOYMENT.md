# Geo Service Deployment Plan

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Pipelines
- CI: lint, unit tests, contract checks; container build and push to ACR.
- CD: ArgoCD sync via `geo-values.yaml`; smoke tests hit REST ingestion and WebSocket handshake.

## Environments
| Environment | Branch/Artifact | Purpose | Approvals |
| --- | --- | --- | --- |
| staging | `main` image tag | Integration with simulators | Auto |
| production | `release/*` or tag | Public demo | PR + manual |

## Release Steps
1. Preconditions: Service Bus topic/subscription `geo-locations` exists; Cosmos `locations` container ready.
2. Deployment: merge -> image build -> values bump -> ArgoCD sync.
3. Verification: publish synthetic location message; verify WebSocket broadcast and Cosmos upsert; check OTEL traces.
4. Rollback: revert Helm values tag; drain WebSocket connections; replay missed messages if needed.

## Infrastructure
- Cosmos DB container `locations` with HPK (`ownerId`, `tripId`, `bucketDate`).
- Service Bus topic `geo-locations`; KEDA ScaledObject on subscription length.
- AKS Deployment with HPA (CPU 70%, min 2, max 10) sized for WebSocket concurrency; separate worker Deployment for queue ingestion if needed.
- Azure Maps dependency; credentials sourced via Managed Identity or rotated key secret reference (no static keys in repo).