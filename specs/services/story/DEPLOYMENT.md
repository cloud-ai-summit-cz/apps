# Story Service Deployment Plan

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Pipelines
- CI: lint, unit tests, contract validation; optional prompt linting; build container image; push to ACR.
- CD: ArgoCD sync of Helm values (`env/{env}/apps/story-values.yaml`) updating image tag; post-deploy smoke (health, `/stories` list) and synthetic story generation.

## Environments
| Environment | Branch/Artifact | Purpose | Approvals |
| --- | --- | --- | --- |
| staging | `main` image tag | Integration with trip/toy/geo | Auto on merge |
| production | `release/*` or tag | Public demo | PR + manual promotion |

## Release Steps
1. Preconditions: green CI; Service Bus queue `story-jobs` reachable; Cosmos container `stories` provisioned.
2. Deployment: merge -> image build -> values bump -> ArgoCD sync.
3. Verification: smoke test `GET /healthz`; trigger one synthetic story; verify Cosmos write and log traces.
4. Rollback: revert Helm values to previous tag; ArgoCD sync; clear in-flight story messages if corrupt payload detected.

## Infrastructure
- Cosmos DB container `stories` (HPK `ownerId`, `tripId`).
- Service Bus queue `story-jobs` for async generation; KEDA ScaledObject on queue length.
- Azure OpenAI model deployment (chat completion) referenced via Managed Identity.
- AKS Deployment with HPA (CPU 70%, min 1, max 5) and optional KEDA worker for queue processing.