# Add-On Service Deployment Plan

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Pipelines
- CI: lint, unit tests, contract checks; build and push container to ACR.
- CD: ArgoCD sync via `addon-values.yaml`; smoke tests cover order creation and health endpoint.

## Environments
| Environment | Branch/Artifact | Purpose | Approvals |
| --- | --- | --- | --- |
| staging | `main` image tag | Integration with Trip and Demo Media | Auto |
| production | `release/*` or tag | Public demo | PR + manual |

## Release Steps
1. Preconditions: Cosmos `addons` container exists; Service Bus queue `addon-fulfill` provisioned; Demo Media endpoint configured.
2. Deployment: merge -> build -> values bump -> ArgoCD sync.
3. Verification: place synthetic order; ensure status updates to `fulfilled` and gallery entry appears via Trip Service.
4. Rollback: revert values tag; drain queue if corrupted payloads; reprocess orders after rollback if needed.

## Infrastructure
- Cosmos DB container `addons` (HPK `ownerId`, `tripId`).
- Service Bus queue `addon-fulfill`; KEDA ScaledObject for worker autoscaling.
- AKS Deployment with HPA (CPU 70%, min 1, max 10) for API; separate worker Deployment for fulfillment queue.
- Azure Storage container for fulfillment images; access via Managed Identity (no SAS exposed).