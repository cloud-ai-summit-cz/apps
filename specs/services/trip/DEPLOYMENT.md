# Service Deployment Plan – Trip Service

This document describes the specific deployment pipeline and configuration for the Trip service. It adheres to the shared strategies defined in `../../platform/DEPLOYMENT.md`.

## Pipeline Overview (`build-trip.yml`)

The deployment pipeline is fully automated for staging and GitOps-driven.

1.  **Trigger**: Push to `src/services/trip/**` or `src/shared/**`.
2.  **Context Loading**: Reads `env/staging/infra_config/azure.yaml` to find the ACR login server.
3.  **Build**: Creates a Docker image from `src/services/trip/Dockerfile`.
4.  **Push**: Pushes tags `latest` and `{commit-sha}` to the shared ACR.
5.  **Config Update**: Modifies `env/staging/apps/trip-values.yaml` with the new image tag.
6.  **Deploy**: ArgoCD detects the Git change and syncs the `trip` application in the cluster.

## Configuration & Dependencies

- **Helm Chart**: `helm-charts/trip/`
- **Values File**: `env/{env}/apps/trip-values.yaml`
- **Infrastructure Dependencies**:
    - **Cosmos DB**: `trips` container (connection via Workload Identity).
    - **Storage**: `gallery` container (connection via Workload Identity).
    - **Toy Service**: HTTP dependency for validating toys.
- **Identity**: Uses Azure Workload Identity. The Client ID is automatically injected into `trip-values.yaml` by the infra pipeline.

## Release Steps

### Staging (Automatic)
1.  Commit changes to `main`.
2.  GitHub Action `Build and Push Trip Service` runs.
3.  Action updates `env/staging/apps/trip-values.yaml`.
4.  ArgoCD syncs the new image.

### Production (Manual)
1.  Identify the stable commit SHA from staging.
2.  Update `env/production/apps/trip-values.yaml` with the target image tag.
3.  Create and merge a Pull Request.
4.  ArgoCD syncs the production cluster.

## Rollback
- **Immediate**: Revert the commit that updated `trip-values.yaml`.
- **ArgoCD**: Will automatically sync back to the previous image tag.

