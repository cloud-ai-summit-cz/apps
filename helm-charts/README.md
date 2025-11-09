# Helm Charts

This directory contains Helm charts for all ToyTrip microservices. Each chart follows minimal conventions, exposing only essential configuration parameters while keeping rarely-changed Kubernetes resources static.

## Available Charts

### toy
**Path**: `helm-charts/toy/`  
**Service**: Toy Service (FastAPI)  
**Port**: 8001  
**Ingress Path**: `/api/toys`

Dependencies:
- Cosmos DB (toys container)
- Blob Storage (avatars container)
- Azure AD authentication

Environment variables:
- `COSMOS_ENDPOINT`
- `STORAGE_ACCOUNT_URL`
- `AZURE_TENANT_ID`
- `APP_ID_URI`

### trip
**Path**: `helm-charts/trip/`  
**Service**: Trip Service (FastAPI)  
**Port**: 8002  
**Ingress Path**: `/api/trips`

Dependencies:
- Cosmos DB (trips container)
- Blob Storage (gallery container)
- Toy Service (internal HTTP calls)
- Azure AD authentication

Environment variables:
- `COSMOS_ENDPOINT`
- `STORAGE_ACCOUNT_URL`
- `TOY_SERVICE_URL`
- `AZURE_TENANT_ID`
- `APP_ID_URI`

### web
**Path**: `helm-charts/web/`  
**Service**: Web Frontend (Nginx)  
**Port**: 80  
**Ingress Path**: `/`

Static React application served by Nginx. No runtime environment variables (configuration injected at build time).

## Chart Structure

Each chart follows standard Helm conventions:

```
<chart-name>/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
└── templates/
    ├── _helpers.tpl        # Template helpers
    ├── deployment.yaml     # Kubernetes Deployment
    ├── service.yaml        # Kubernetes Service
    ├── ingress.yaml        # Ingress (AKS App Routing)
    └── serviceaccount.yaml # ServiceAccount
```

## Key Configuration Parameters

### Common (all charts)
- `image.repository`: Container image repository (e.g., `myacr.azurecr.io/toy-service`)
- `image.tag`: Image tag (typically commit SHA for immutability)
- `replicaCount`: Number of pod replicas
- `resources`: CPU and memory limits/requests
- `ingress.enabled`: Enable/disable ingress
- `ingress.hosts`: Ingress host and path configuration

### Service-specific
- `env`: Dictionary of environment variables
- `workloadIdentity.enabled`: Enable Azure Workload Identity
- `workloadIdentity.clientId`: Managed Identity client ID

## Ingress Configuration

All charts use AKS App Routing with NGINX:

```yaml
ingress:
  enabled: true
  className: "webapprouting.kubernetes.azure.com"
  hosts:
    - host: "example.com"  # or "" for IP-based
      paths:
        - path: /api/toys
          pathType: Prefix
```

The App Routing addon provides:
- Managed NGINX ingress controller
- Automatic load balancer provisioning
- Optional Azure DNS integration
- Optional TLS with Azure Key Vault

## Usage in ArgoCD

Charts are deployed via ArgoCD using multi-source pattern:

1. **Chart source**: `helm-charts/<service>/`
2. **Values source**: `env/<environment>/apps/<service>-values.yaml`

Example Application manifest:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: toy-service
  namespace: argocd
spec:
  sources:
    - repoURL: https://github.com/cloud-ai-summit-cz/apps.git
      targetRevision: main
      path: helm-charts/toy
      helm:
        valueFiles:
          - $values/env/staging/apps/toy-values.yaml
    - repoURL: https://github.com/cloud-ai-summit-cz/apps.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: toytrip-staging
```

## Local Development

Test charts locally using Helm:

```bash
# Lint chart
helm lint helm-charts/toy

# Dry-run with custom values
helm install toy-test helm-charts/toy \
  --dry-run \
  --values env/staging/apps/toy-values.yaml

# Template and inspect output
helm template toy helm-charts/toy \
  --values env/staging/apps/toy-values.yaml \
  > /tmp/toy-manifests.yaml
```

## Extending Charts

When adding new configuration:

1. **Add to `values.yaml`**: Define sensible defaults
2. **Reference in templates**: Use `{{ .Values.newParameter }}`
3. **Update environment values**: Override in `env/<env>/apps/<service>-values.yaml`
4. **Document**: Update this README and chart README if adding complex features

Keep changes minimal—only add configuration that genuinely varies per deployment.
