# Service Deployment Plan – Demo Data Init

This document describes the specific deployment pipeline and configuration for the Demo Data Init service. It adheres to the shared strategies defined in `../../platform/DEPLOYMENT.md`.

## Pipeline Overview (`build-demo-data-init.yml`)

The deployment pipeline is fully automated for staging and GitOps-driven.

1.  **Trigger**: Push to `src/services/demo-data-init/**` or `src/shared/**`.
2.  **Context Loading**: Reads `env/staging/infra_config/azure.yaml` to find the ACR login server.
3.  **Build**: Creates a Docker image from `src/services/demo-data-init/Dockerfile`.
4.  **Push**: Pushes tags `latest` and `{commit-sha}` to the shared ACR.
5.  **Config Update**: Modifies `env/staging/apps/demo-data-init-values.yaml` with the new image tag.
6.  **Deploy**: ArgoCD detects the Git change and syncs the `demo-data-init` application in the cluster.

## Configuration & Dependencies

- **Helm Chart**: `helm-charts/demo-data-init/`
- **Values File**: `env/{env}/apps/demo-data-init-values.yaml`
- **Infrastructure Dependencies**:
    - **Cosmos DB**: `toys` and `trips` containers (connection via Workload Identity).
    - **Storage**: `avatars` and `gallery` containers (connection via Workload Identity).
- **Identity**: Uses Azure Workload Identity. The Client ID is automatically injected into `demo-data-init-values.yaml` by the infra pipeline.

## Release Steps

### Staging (Automatic)
1.  Commit changes to `main`.
2.  GitHub Action `Build and Push Demo Data Init Service` runs.
3.  Action updates `env/staging/apps/demo-data-init-values.yaml`.
4.  ArgoCD syncs the new image.

### Production
*Note: This service is typically not deployed or is disabled in production environments to prevent accidental data overwrites.*

## Rollback
- **Immediate**: Revert the commit that updated `demo-data-init-values.yaml`.
- **ArgoCD**: Will automatically sync back to the previous image tag.

