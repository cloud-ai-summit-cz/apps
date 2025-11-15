# Helm Charts

This directory contains Helm charts for all ToyTrip microservices. Each chart follows minimal conventions, exposing only essential configuration parameters while keeping rarely-changed Kubernetes resources static.

## Available Charts

### Platform Components

#### platform-gateway
**Path**: `helm-charts/platform-gateway/`  
**Purpose**: Shared Istio Gateway + TLS certificate  
**Resources**: Gateway API `Gateway`, cert-manager `Certificate`

Features:
- Binds the managed Istio ingress gateway to the pre-created static public IP
- Emits listener definitions (hostname, protocol, TLS mode) from env-specific values
- Optionally provisions the cert-manager `Certificate` that backs the listener's secret

Values:
- `gateway.name`: Logical name for the Gateway (referenced by HTTPRoutes)
- `gateway.listeners[]`: Host, port, protocol, TLS settings, and allowedRoutes
- `certificate.*`: ClusterIssuer, secretName, and DNS names (optional)

#### platform-cert-manager
**Path**: `helm-charts/platform-cert-manager/`  
**Purpose**: cert-manager installation with Let's Encrypt configuration  
**Resources**: cert-manager Helm chart + ClusterIssuer CRDs

Provides automatic TLS certificate management:
- Installs cert-manager v1.16.2 from Jetstack
- Creates Let's Encrypt ClusterIssuers (staging + production)
- HTTP-01 challenge served through the shared Istio Gateway listener

Values:
- `environment`: "staging" or "production" (determines issuer deployment)
- `letsencrypt.email`: Email for Let's Encrypt notifications

### Application Services

#### toy
**Path**: `helm-charts/toy/`  
**Service**: Toy Service (FastAPI)  
**Port**: 8001  
**HTTPRoute Path**: `/api/toys`

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
**HTTPRoute Path**: `/api/trips`

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
**HTTPRoute Path**: `/`

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
  ├── httproute.yaml      # Gateway API HTTPRoute (per service)
  ├── gateway.yaml        # Shared Gateway (platform chart only)
  └── serviceaccount.yaml # ServiceAccount
```

## Key Configuration Parameters

### Common (all charts)
- `image.repository`: Container image repository (e.g., `myacr.azurecr.io/toy-service`)
- `image.tag`: Image tag (typically commit SHA for immutability)
- `replicaCount`: Number of pod replicas
- `resources`: CPU and memory limits/requests
- `httpRoute.enabled`: Enable/disable Gateway API routing
- `httpRoute.parentRefs`: List of `Gateway` references each route should attach to
- `httpRoute.hosts[]`: Host + path match configuration per service

### Service-specific
- `env`: Dictionary of environment variables
- `workloadIdentity.enabled`: Enable Azure Workload Identity
- `workloadIdentity.clientId`: Managed Identity client ID

## Gateway API HTTPRoute Configuration

All service charts now attach to the shared Istio gateway via HTTPRoute resources:

```yaml
httpRoute:
  enabled: true
  parentRefs:
    - group: gateway.networking.k8s.io
      kind: Gateway
      name: web-frontend-gateway
      namespace: toytrip-staging
  hosts:
    - host: "appdemo-eniwvl.swedencentral.cloudapp.azure.com"
      paths:
        - path: /api/toys
          pathType: PathPrefix
```

The `platform-gateway` chart manages the actual `Gateway` resource and TLS secrets; services simply define the host/path matches and backend service port. Update the `parentRefs` section whenever the gateway name or namespace changes.

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
