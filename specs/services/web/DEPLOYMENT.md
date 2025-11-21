# Service Deployment Plan – Web Frontend

This document describes the specific deployment pipeline and configuration for the Web Frontend. It adheres to the shared strategies defined in `../../platform/DEPLOYMENT.md`.

## Pipeline Overview (`build-web.yml`)

The deployment pipeline is fully automated for staging and GitOps-driven.

1.  **Trigger**: Push to `src/web/**`.
2.  **Context Loading**: Reads `env/staging/infra_config/azure.yaml` to find the ACR login server.
3.  **Build**:
    - Installs dependencies (`npm install`).
    - Builds static assets (`npm run build`).
    - Creates a Docker image from `src/web/Dockerfile` (Nginx-based).
4.  **Push**: Pushes tags `latest` and `{commit-sha}` to the shared ACR.
5.  **Config Update**: Modifies `env/staging/apps/web-values.yaml` with the new image tag.
6.  **Deploy**: ArgoCD detects the Git change and syncs the `web` application in the cluster.

## Runtime Configuration
The application uses the **"Build once, deploy anywhere"** pattern.
- **Mechanism**: `docker-entrypoint.sh` reads environment variables (`VITE_API_BASE_URL`, etc.) at runtime and writes them to `env-config.js` in the Nginx html root.
- **Client**: The frontend code reads from `window.ENV_CONFIG` to know which backend API to call.

## Configuration & Dependencies

- **Helm Chart**: `helm-charts/web/`
- **Values File**: `env/{env}/apps/web-values.yaml`
- **Infrastructure Dependencies**:
    - **Ingress**: Exposed via the shared Istio Gateway.
    - **Backend APIs**: Depends on `toy` and `trip` services being reachable via the Gateway.

## Release Steps

### Staging (Automatic)
1.  Commit changes to `main`.
2.  GitHub Action `Build and Push Web Service` runs.
3.  Action updates `env/staging/apps/web-values.yaml`.
4.  ArgoCD syncs the new image.

### Production (Manual)
1.  Identify the stable commit SHA from staging.
2.  Update `env/production/apps/web-values.yaml` with the target image tag.
3.  Create and merge a Pull Request.
4.  ArgoCD syncs the production cluster.

## Rollback
- **Immediate**: Revert the commit that updated `web-values.yaml`.
- **ArgoCD**: Will automatically sync back to the previous image tag.

