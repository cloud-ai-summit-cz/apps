# Deployment

## Infrastructure Overview

### Network Architecture

**Virtual Network Design:**
- **Address Space:** `10.240.0.0/16`
- **Subnets:**
  - `snet-aks-nodes` (`10.240.0.0/22`) - AKS cluster nodes with CNI Overlay
  - `snet-aks-api` (`10.240.4.0/28`) - AKS API server VNET integration (delegated to Microsoft.ContainerService)
  - `snet-private-endpoints` (`10.240.5.0/24`) - Private endpoints for Azure services

**NAT Gateway:**
- Zone-redundant NAT Gateway with 2 public IPs across availability zones
- Attached to `snet-aks-nodes` for outbound connectivity
- Provides stable outbound IPs for external service integration

**Private DNS Zones:**
- `privatelink.documents.azure.com` - Cosmos DB private DNS resolution
- `privatelink.blob.core.windows.net` - Storage Account private DNS resolution
- `privatelink.azurecr.io` - Azure Container Registry private DNS resolution
- All zones linked to VNet for automatic DNS resolution

### Kubernetes Platform

**AKS Automatic Cluster:**
- **Mode:** Automatic (fully managed node provisioning)
- **SKU:** Standard tier with SLA
- **Networking:**
  - Azure CNI Overlay with Cilium dataplane
  - Cilium network policy engine
  - Advanced Container Networking Services for observability
  - API server with VNET integration (public endpoint + private network access)
  - Outbound via user-assigned NAT Gateway
- **Identity:**
  - User-assigned managed identity for cluster control plane
  - Separate kubelet identity with AcrPull role for container image pulling
- **Security:**
  - Workload identity enabled (OIDC federation)
  - Azure RBAC for Kubernetes authorization
  - Local accounts disabled (Azure AD only)
  - Image cleaner enabled (removes vulnerable images daily)
  - Automatic security patches via node image auto-upgrade
- **Scaling:** Node auto-provisioning based on workload demands
- **Monitoring:** Integrated Managed Prometheus and Container Insights

### Container Registry

**Azure Container Registry (Premium):**
- Zone-redundant storage
- Admin user disabled (managed identity authentication only)
- Public network access enabled by default (can be disabled with private endpoints)
- Network rule bypass for Azure Services
- Kubelet identity has AcrPull role for seamless image pulling

### Data Services

**Cosmos DB (SQL API, Serverless):**
- Serverless capacity mode (pay-per-operation)
- Session consistency level
- Key-based metadata write disabled (control plane only via Bicep)
- Database: `toytripdb`
- Containers: `toys` (partition key: `/toy_id`), `trips` (partition key: `/trip_id`)
- Optional private endpoint support

**Storage Account (Standard ZRS):**
- Zone-redundant storage
- TLS 1.2 minimum
- Public blob access disabled
- Containers: `avatars`, `gallery`
- Optional private endpoint support

### Private Endpoint Strategy

**Toggle:** Controlled by `enablePrivateEndpoints` parameter (default: `false`)

When enabled:
- Disables public network access for ACR, Cosmos DB, and Storage Account
- Creates private endpoints in `snet-private-endpoints` subnet
- Configures private DNS zone groups for automatic DNS resolution
- All traffic flows through private IPs within VNet

**Recommendation:** Keep disabled during development/testing, enable for production deployments.

### Role-Based Access Control

**User Access:**
- Storage Blob Data Contributor on Storage Account
- Cosmos DB Built-in Data Contributor on Cosmos Account

**Service Identity:**
- AKS kubelet identity: AcrPull on resource group (for pulling images)
- AKS cluster identity: Network Contributor (automatically assigned by AKS)

## Deployment Process

### Prerequisites
- Azure CLI or PowerShell
- Appropriate Azure subscription permissions
- User object ID for RBAC assignments

### Deploy Infrastructure

```bash
# Set parameters
RESOURCE_GROUP="rg-toytrip-dev"
LOCATION="eastus"
PREFIX="toytrip"
USER_OBJECT_ID="<your-azure-ad-user-object-id>"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy Bicep template
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/bicep/main.bicep \
  --parameters prefix=$PREFIX \
               userObjectId=$USER_OBJECT_ID \
               location=$LOCATION \
               enablePrivateEndpoints=false
```

### Access AKS Cluster

```bash
# Get credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name <aks-cluster-name>

# Verify connectivity
kubectl get nodes
```

### Build and Push Container Images

```bash
# Login to ACR
az acr login --name <acr-name>

# Build and push images (example for toy service)
docker build -t <acr-name>.azurecr.io/toy-service:latest ./src/services/toy
docker push <acr-name>.azurecr.io/toy-service:latest
```

### AKS App Routing (Automated)

The AKS App Routing add-on is **automatically enabled** during infrastructure deployment via Bicep:

```bicep
// In infra/bicep/modules/aksAutomatic.bicep
ingressProfile: {
  webAppRouting: {
    enabled: true
    nginx: {
      defaultIngressControllerType: 'AnnotationControlled'
    }
  }
}
```

After deployment, verify the ingress controller:

```bash
# Get cluster credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name <aks-cluster-name>

# Verify ingress class
kubectl get ingressclass
# Should see: webapprouting.kubernetes.azure.com

# Get the ingress controller IP
kubectl get service -n app-routing-system nginx -o jsonpath="{.status.loadBalancer.ingress[0].ip}"
```

### Bootstrap ArgoCD (Automated with Infrastructure)

ArgoCD installation and configuration is fully integrated into the infrastructure deployment workflow. The `deploy-infra.yml` workflow:
- Deploys all Azure resources (AKS, ACR, Storage, Cosmos DB)
- Installs and configures ArgoCD automatically using AKS run command
- Applies the root application to bootstrap all services
- Eliminates the need for manual bootstrapping or separate workflows

**Prerequisites:**
1. GitHub secret `ARGOCD_REPO_TOKEN` configured with PAT having `repo` scope

**Deployment:**

Simply run the infrastructure deployment workflow:

```bash
# Via GitHub CLI
gh workflow run deploy-infra.yml

# Or via GitHub UI:
# Actions → Deploy Infrastructure → Run workflow

# Or automatically on push to infra/bicep/**
git push
```

The workflow automatically performs:
1. **Deploy Infrastructure**: Creates/updates all Azure resources via Bicep
2. **Generate Config**: Writes `env/staging/infra_config/azure.yaml` with deployment outputs
3. **Install ArgoCD**: Creates namespace and applies manifests using `az aks command invoke`
4. **Configure Repository Access**: Creates secret with GitHub PAT for private repo access
5. **Apply Root Application**: Deploys the app-of-apps manifest to bootstrap all services

**What happens behind the scenes:**

```bash
# 1. Install ArgoCD
az aks command invoke \
  --resource-group $RG \
  --name $AKS_CLUSTER \
  --command "kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - && \
             kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"

# 2. Configure repo access (using secret from GitHub)
az aks command invoke \
  --resource-group $RG \
  --name $AKS_CLUSTER \
  --file repo-secret.yaml \
  --command "kubectl apply -f repo-secret.yaml"

# 3. Apply root app
az aks command invoke \
  --resource-group $RG \
  --name $AKS_CLUSTER \
  --file env/staging/bootstrap/root-app.yaml \
  --command "kubectl apply -f root-app.yaml"
```

**Access ArgoCD UI:**

After bootstrap completes:

```bash
# Get cluster credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name <aks-cluster-name>

# Port-forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (displayed in workflow output)
```

**Manual Bootstrap (Alternative):**

If you need to bootstrap manually without the workflow:

```bash
# 1. Get cluster credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name <aks-cluster-name>

# 2. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Configure repository access
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: repo-apps
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: https://github.com/cloud-ai-summit-cz/apps.git
  username: git
  password: <github-token>
EOF

# 4. Apply root app
kubectl apply -f env/staging/bootstrap/root-app.yaml

# 5. Watch applications sync
kubectl get applications -n argocd -w
```

## ArgoCD GitOps Strategy

### Overview
We use ArgoCD with an "app of apps" pattern to declaratively manage all microservice deployments. Source of truth lives in this repository; ArgoCD continuously reconciles the desired state in Git with the running state in the AKS cluster.

### Repository Layout (GitOps Directories)
```
helm-charts/
  <service-a>/Chart.yaml
  <service-a>/templates/*.yaml
  <service-b>/...
env/
  staging/
    infra_config/
      azure.yaml              # infrastructure outputs (ACR, storage, cosmos, aks, resourceGroup)
    apps/
      service-a-values.yaml   # image.tag, resources, replicas, env overrides for staging
      service-b-values.yaml
    bootstrap/
      root-app.yaml           # ArgoCD Application (app of apps) referencing child apps
  production/
    infra_config/
      azure.yaml              # (optionally promoted / copied when infra differs per environment)
    apps/
      service-a-values.yaml   # production specific overrides
      service-b-values.yaml
    bootstrap/
      root-app.yaml
```

### Infrastructure Outputs Propagation (`azure.yaml`)
An automated GitHub Actions workflow (`deploy-infra.yml`) deploys the Bicep template to the resource group `rg-appdemo` using OIDC federated credentials, then writes key outputs into `env/staging/infra_config/azure.yaml` with the following schema:

```yaml
# env/staging/infra_config/azure.yaml
resourceGroup: rg-appdemo
acr:
  name: <acrName>
  loginServer: <acrLoginServer>
aks:
  name: <aksClusterName>
  oidcIssuerUrl: <aksOidcIssuerUrl>
storage:
  accountId: <storageAccountId>
  accountName: <derived-from-id>
cosmos:
  accountId: <cosmosAccountId>
  accountName: <derived-from-id>
generatedAt: <ISO8601 timestamp>
```

Only values that change (e.g., on first deployment or infra drift requiring recreation) result in a commit with message:
```
Automation - Infrastructure config
```
The workflow intentionally **does not** trigger service image rebuilds (values files are separate) but allows ArgoCD (multi-source or valueFiles) to reference ACR login server or other infra data if needed.

### Using `azure.yaml` in Workflows & ArgoCD
* **Build Workflows:** Can parse `env/staging/infra_config/azure.yaml` (e.g. with `yq`) to set `ACR_NAME` / `ACR_LOGIN_SERVER` instead of hardcoding.
* **Helm Charts:** Optionally load selected values (e.g. `acr.loginServer`) via a ConfigMap or inject as environment variables referencing cluster secrets—kept minimal here.
* **Promotion:** If production uses a distinct infrastructure deployment, a corresponding `env/production/infra_config/azure.yaml` is created by running the infra workflow with `environment: production` (future enhancement). Otherwise, copy or cherry-pick the staging file when promoting.

### Rationale
Centralizing infra outputs as versioned YAML inside the Git repo ensures:
1. **Determinism:** Git history reflects infra evolution.
2. **Single Source of Truth:** Both CI and GitOps CD read identical values.
3. **Security Boundary:** Only non-secret identifiers are stored (no connection strings/keys). Secrets remain in Azure or sealed secret stores.
4. **Low Coupling:** Application value files remain focused on deploy-time app settings; infra YAML changes rarely.

> Note: If future outputs (e.g., Key Vault names) are required, extend the Bicep outputs and append new keys to `azure.yaml` without breaking existing consumers (treat additions as backward-compatible).

### Helm Chart Conventions
Each microservice has a minimal chart focusing on only the most commonly tuned attributes:
* Image repository & tag
* Replicas count
* Resource requests & limits
* Liveness / readiness probes (toggle & paths if applicable)
* Environment variables / config map references (only essential)
* Service type & port

Non‑critical or rarely changed Kubernetes fields remain static within `templates/` to reduce maintenance overhead and cognitive load.

#### Implemented Charts
Three Helm charts are provided in `helm-charts/`:

1. **toy** (`helm-charts/toy/`)
   - FastAPI service on port 8001
   - Ingress path: `/api/toys`
   - Environment: Cosmos DB (toys container), Blob Storage (avatars)

2. **trip** (`helm-charts/trip/`)
   - FastAPI service on port 8002
   - Ingress path: `/api/trips`
   - Environment: Cosmos DB (trips container), Blob Storage (gallery), inter-service call to toy service

3. **web** (`helm-charts/web/`)
   - Nginx static frontend on port 80
   - Ingress path: `/` (root)
   - No runtime environment variables (build-time configuration)

All charts use `ingressClassName: webapprouting.kubernetes.azure.com` for AKS App Routing with managed NGINX ingress.

### Image Tagging & Build Workflow
1. Developer merges or pushes to main (or feature branch for preview if extended later).
2. GitHub Actions workflow builds each changed microservice image.
3. Image is tagged with immutable commit SHA (e.g. `toy-service:<git-sha>`).
4. For staging environment only: workflow updates the corresponding `env/staging/apps/<service>-values.yaml` file, setting `image.tag` to the new commit SHA.
  - ACR name & login server now sourced dynamically (if desired) from `env/staging/infra_config/azure.yaml` instead of hardcoding.
5. Workflow commits the change back to the repository (fast‑forward or PR merge strategy—ensure bot account has permission).
6. ArgoCD detects the changed values file and reconciles, rolling out the new image to staging.

Production values are updated via an intentional promotion step (manual PR) to ensure controlled releases.

### App of Apps Bootstrap
`env/<environment>/bootstrap/root-app.yaml` defines an ArgoCD Application that points at the `env/<environment>/apps` directory. Each microservice ArgoCD Application is defined either as child manifests within that folder or via an optional ApplicationSet (future enhancement) to reduce repetition.

#### Bootstrap Process
1. Install ArgoCD in the AKS cluster (standard installation)
2. Apply the root application manifest: `kubectl apply -f env/staging/bootstrap/root-app.yaml`
3. ArgoCD discovers child applications in `env/staging/apps/`:
   - `toy-app.yaml` → Deploys toy service
   - `trip-app.yaml` → Deploys trip service
   - `web-app.yaml` → Deploys web frontend
4. Each child application uses multi-source pattern:
   - Source 1: Helm chart from `helm-charts/<service>/`
   - Source 2: Service-specific values from `env/staging/apps/<service>-values.yaml`

All services deploy to `toytrip-staging` namespace (auto-created).

### Promotion Flow
* Staging soak verification (integration tests, manual checks)
* Create PR copying validated commit SHAs from `env/staging/apps/*.yaml` to `env/production/apps/*.yaml`
* Merge PR – ArgoCD syncs production

### Sync & Drift Policies
* Automated sync enabled for staging (auto‑prune & self‑heal)
* Manual sync (or auto without prune) for production to allow controlled rollout & rapid rollback (revert Git commit)

### Rollback
Rollback is a Git revert of the values file changes to a prior commit SHA; ArgoCD reconciliation rolls the deployment back (leveraging image immutability).

### Benefits
* Deterministic deployments (Git = source of truth)
* Fast promotion via SHA copy
* Minimal surface of change (only values files mutate post‑merge)
* Clear audit trail of each deployment via Git history

### Operational Notes
* Ensure ArgoCD has read access (deploy key / PAT) to the repository.
* Consider enabling notifications (Slack / Teams) for sync & health events.
* Namespace strategy: Using single `toytrip-staging` namespace for all staging services.

### CI/CD Image Update Workflow
When service code changes are merged to main:

1. **Build & Push**: GitHub Actions builds container image tagged with commit SHA
   - Parse `env/staging/infra_config/azure.yaml` to get ACR login server
   - Build: `docker build -t <acr>.azurecr.io/<service>:<sha>`
   - Push to ACR

2. **Update Values**: Same workflow updates `env/staging/apps/<service>-values.yaml`:
   ```yaml
   image:
     repository: <acr>.azurecr.io/<service>
     tag: <commit-sha>
   ```

3. **Commit Back**: Workflow commits change with message:
   ```
   Automation - Update <service> image to <sha>
   ```

4. **ArgoCD Sync**: ArgoCD detects Git change and reconciles deployment (automated for staging)

5. **Verification**: Check sync status: `kubectl get application -n argocd`

**Example workflow additions** (add to `.github/workflows/<service>-build.yml`):
```yaml
- name: Get ACR details
  run: |
    ACR_LOGIN_SERVER=$(yq '.acr.loginServer' env/staging/infra_config/azure.yaml)
    echo "ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER" >> $GITHUB_ENV

- name: Update staging values
  run: |
    yq -i ".image.repository = \"$ACR_LOGIN_SERVER/$SERVICE_NAME\"" env/staging/apps/$SERVICE_NAME-values.yaml
    yq -i ".image.tag = \"$GITHUB_SHA\"" env/staging/apps/$SERVICE_NAME-values.yaml

- name: Commit values update
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add env/staging/apps/$SERVICE_NAME-values.yaml
    git commit -m "Automation - Update $SERVICE_NAME image to $GITHUB_SHA"
    git push
```

## Future Enhancements
- Application Gateway Ingress Controller
- Azure Key Vault integration for secrets management
- Network policies for pod-to-pod traffic control
- ArgoCD ApplicationSet for dynamic app generation
- Progressive delivery (Blue/Green or Canary) with Argo Rollouts

