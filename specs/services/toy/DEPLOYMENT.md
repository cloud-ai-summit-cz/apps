# Service Deployment Plan – Toy Service

This document describes the specific deployment pipeline and configuration for the Toy service. It adheres to the shared strategies defined in `../../platform/DEPLOYMENT.md`.

## Pipeline Overview (`build-toy.yml`)

The deployment pipeline is fully automated for staging and GitOps-driven.

1.  **Trigger**: Push to `src/services/toy/**` or `src/shared/**`.
2.  **Context Loading**: Reads `env/staging/infra_config/azure.yaml` to find the ACR login server.
3.  **Build**: Creates a Docker image from `src/services/toy/Dockerfile`.
4.  **Push**: Pushes tags `latest` and `{commit-sha}` to the shared ACR.
5.  **Config Update**: Modifies `env/staging/apps/toy-values.yaml` with the new image tag.
6.  **Deploy**: ArgoCD detects the Git change and syncs the `toy` application in the cluster.

## Configuration & Dependencies

- **Helm Chart**: `helm-charts/toy/`
- **Values File**: `env/{env}/apps/toy-values.yaml`
- **Infrastructure Dependencies**:
    - **Cosmos DB**: `toys` container (connection via Workload Identity).
    - **Storage**: `avatars` container (connection via Workload Identity).
    - **Observability**: `otel-collector` (via `OTEL_EXPORTER_OTLP_ENDPOINT`).
- **Identity**: Uses Azure Workload Identity. The Client ID is automatically injected into `toy-values.yaml` by the infra pipeline.

## Release Steps

### Staging (Automatic)
1.  Commit changes to `main`.
2.  GitHub Action `Build and Push Toy Service` runs.
3.  Action updates `env/staging/apps/toy-values.yaml`.
4.  ArgoCD syncs the new image.

### Production (Manual)
1.  Identify the stable commit SHA from staging.
2.  Update `env/production/apps/toy-values.yaml` with the target image tag.
3.  Create and merge a Pull Request.
4.  ArgoCD syncs the production cluster.

## Rollback
- **Immediate**: Revert the commit that updated `toy-values.yaml`.
- **ArgoCD**: Will automatically sync back to the previous image tag.

