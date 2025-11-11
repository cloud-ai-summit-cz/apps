# Azure Infrastructure - Bicep Templates

## Overview
Complete Azure infrastructure for the ToyTrip application including:
- **AKS Automatic**: Kubernetes cluster with CNI Overlay, Cilium, and auto-provisioning
- **Azure Container Registry**: Premium tier with zone redundancy
- **Cosmos DB**: Serverless SQL API with database + containers
- **Storage Account**: Zone-redundant blob storage
- **Networking**: Custom VNet, NAT Gateway, private DNS zones
- **Security**: User-assigned managed identities, optional private endpoints
- **Role Assignments**: Storage Blob Data Contributor & Cosmos DB Built-in Data Contributor

Naming suffix derived from `uniqueString(subscription().id, prefix)` with digits mapped to letters (0→a ... 9→j) to satisfy letter-only requirement.

## Prerequisites
- Azure CLI 2.64.0+ (for Bicep with AKS Automatic support)
- Correct subscription selected: `az account set -s <subscriptionId>`

## Deployment

### Get Your Object ID
```pwsh
$objectId = az ad signed-in-user show --query id -o tsv
```

## Create Resource Group
```pwsh
$rg='rg-appdemo'
az group create -n $rg -l swedencentral
```

## Deploy
Update `infra/bicep/main.parameters.bicepparam` with your objectId.

```pwsh
az deployment group create -g $rg -f main.bicep -p main.parameters.bicepparam
```

### Post-Deployment Setup

**Get AKS Credentials:**
```pwsh
az aks get-credentials --resource-group $rg --name aks-toytrip-<suffix>
kubectl get nodes
```

**Platform Configuration (Automated via ArgoCD):**

The ingress controller and cert-manager are automatically configured by ArgoCD after bootstrap:
- NGINX ingress configured with static public IP and HTTPS redirect
- cert-manager installed with Let's Encrypt ClusterIssuers
- Platform apps deploy from `env/staging/platform/` via ArgoCD

See `docs/DEPLOYMENT.md` for ArgoCD bootstrap instructions.

**Login to ACR:**
```pwsh
$acrName = az deployment group show -g $rg -n main --query properties.outputs.acrName.value -o tsv
az acr login --name $acrName
```

**Build and Push Container Images:**
```pwsh
# From repository root
cd src/services/toy
docker build -t ${acrName}.azurecr.io/toy-service:latest .
docker push ${acrName}.azurecr.io/toy-service:latest

cd ../trip
docker build -t ${acrName}.azurecr.io/trip-service:latest .
docker push ${acrName}.azurecr.io/trip-service:latest
```

## Inspect Outputs
```pwsh
az deployment group show -g $rg -n main --query properties.outputs
```

## Architecture

### Network Design
- **VNet**: 10.240.0.0/16
  - `aks-nodes` subnet: 10.240.0.0/20 (4096 IPs) - delegated to AKS
  - `aks-api` subnet: 10.240.16.0/28 (16 IPs) - delegated to Microsoft.ContainerService/managedClusters
  - `private-endpoints` subnet: 10.240.16.16/28 (16 IPs)
- **NAT Gateway**: Zone-redundant with public IP across zones 1, 2, 3
- **Ingress Public IP**: Zone-redundant Standard SKU with DNS label for AKS ingress controller
- **Private DNS Zones**: Cosmos DB, Blob Storage, ACR (with VNet links)

### AKS Automatic Configuration
- **Node Provisioning**: Fully automatic with AI-driven scaling
- **Networking**: Azure CNI Overlay + Cilium dataplane + Cilium network policies
- **Observability**: Managed Prometheus, Container Insights, Advanced Container Networking Services
- **Endpoint**: Public with VNET integration (aks-api subnet)
- **Security**: Workload identity enabled, Azure RBAC, no local accounts
- **Identities**: Separate UAMIs for cluster control plane and kubelet (with AcrPull)
- **App Routing**: NGINX ingress controller with preconfigured public IP and DNS, HTTPS redirect enabled

### Container Registry
- **SKU**: Premium with zone redundancy
- **Authentication**: Managed identity only (admin user disabled)
- **Private Endpoint**: Optional (controlled by enablePrivateEndpoints parameter)

## Delete (Destroy Environment)
Non-blocking delete:
```pwsh
az group delete -n $rg -y --no-wait
```
Blocking delete (wait until finished):
```pwsh
az group delete -n $rg -y
```

## Modules

| Module | Purpose |
|--------|---------|
| `networking.bicep` | VNet, NAT Gateway, public IPs (NAT + ingress), subnets, private DNS zones |
| `aksAutomatic.bicep` | AKS Automatic cluster with CNI Overlay + Cilium + ACNS + App Routing |
| `acr.bicep` | Azure Container Registry (Premium, zone-redundant) |
| `cosmosSqlServerless.bicep` | Cosmos DB SQL API (serverless) with optional PE |
| `storageAccount.bicep` | Zone-redundant blob storage with optional PE |
| `rbacAssignments.bicep` | Azure RBAC role assignments (ACR Pull, Network Contributor, etc.) |
| `cosmosRoleAssignments.bicep` | Cosmos DB Built-in Data Contributor role assignment |

## Notes
- Role assignment propagation may take up to ~60s before effective.
- Suffix transformation removes digits to satisfy naming convention request; storage account still allows numbers but we keep deterministic pattern.
