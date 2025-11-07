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
    apps/
      service-a-values.yaml   # image.tag, resources, replicas, env overrides for staging
      service-b-values.yaml
    bootstrap/
      root-app.yaml           # ArgoCD Application (app of apps) referencing child apps
  production/
    apps/
      service-a-values.yaml   # production specific overrides
      service-b-values.yaml
    bootstrap/
      root-app.yaml
```

### Helm Chart Conventions
Each microservice has a minimal chart focusing on only the most commonly tuned attributes:
* Image repository & tag
* Replicas count
* Resource requests & limits
* Liveness / readiness probes (toggle & paths if applicable)
* Environment variables / config map references (only essential)
* Service type & port

Non‑critical or rarely changed Kubernetes fields remain static within `templates/` to reduce maintenance overhead and cognitive load.

### Image Tagging & Build Workflow
1. Developer merges or pushes to main (or feature branch for preview if extended later).
2. GitHub Actions workflow builds each changed microservice image.
3. Image is tagged with immutable commit SHA (e.g. `toy-service:<git-sha>`).
4. For staging environment only: workflow updates the corresponding `env/staging/apps/<service>-values.yaml` file, setting `image.tag` to the new commit SHA.
5. Workflow commits the change back to the repository (fast‑forward or PR merge strategy—ensure bot account has permission).
6. ArgoCD detects the changed values file and reconciles, rolling out the new image to staging.

Production values are updated via an intentional promotion step (manual PR) to ensure controlled releases.

### App of Apps Bootstrap
`env/<environment>/bootstrap/root-app.yaml` defines an ArgoCD Application that points at the `env/<environment>/apps` directory. Each microservice ArgoCD Application is defined either as child manifests within that folder or via an optional ApplicationSet (future enhancement) to reduce repetition.

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
* Namespace strategy: either one shared `services` namespace or per‑service namespaces—document chosen convention in future update if diverging.

## Future Enhancements
- Application Gateway Ingress Controller
- Azure Key Vault integration for secrets management
- Network policies for pod-to-pod traffic control
- ArgoCD ApplicationSet for dynamic app generation
- Progressive delivery (Blue/Green or Canary) with Argo Rollouts

