# Shared Deployment Strategy

Capture the release workflow and infrastructure expectations that apply across all services in the monorepo. This reflects the GitOps and Bicep-based approach currently documented under `infra/` and `env/`.

## Environments
| Environment | Purpose | Source Branch / Tag | Promotion Criteria |
| --- | --- | --- | --- |
| staging | Integration + demo environment | main | All checks green on main |
| production | Public demo environment | tagged release / protected branch | Manual approval, promotion from staging |

## CI/CD Pipeline
- Bicep-based infra deployment (`infra/bicep/main.bicep`) producing `env/<env>/infra_config/azure.yaml`.
- ArgoCD-based GitOps bootstrap from `env/<env>/bootstrap/` and `env/<env>/apps/`.
- Service image build pipelines per service (toy, trip, web, demo-data-init) updating Helm values.

## Release Patterns
- Rolling updates via ArgoCD + Kubernetes Deployments.
- Rollback via Git revert + ArgoCD sync.

## Approvals & Compliance
- Infra changes require review.
- Production app changes gated via PRs and approvals.

## Specification by Example
Add concrete scenarios such as "Given a failed canary, the pipeline halts and rolls back within 5 minutes" as you refine deployment behavior.
