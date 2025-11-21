# Platform Observability Helm Chart

OpenTelemetry Collector and Aspire Dashboard for centralized observability.

## Overview

This Helm chart deploys the observability stack for the platform:

1. **OpenTelemetry Collector** - Receives telemetry from all services via OTLP (gRPC/HTTP)
2. **Aspire Dashboard** - Developer-focused UI for visualizing logs, metrics, and traces

## Architecture

```
Services (toy, trip, etc.)
    |
    | OTLP gRPC (port 4317)
    v
OpenTelemetry Collector
    |
    | OTLP (port 18889)
    v
Aspire Dashboard (UI on port 18888)
```

## Components

### OpenTelemetry Collector

- **Image**: `otel/opentelemetry-collector-contrib:0.115.1`
- **Receivers**: OTLP gRPC (4317), OTLP HTTP (4318)
- **Processors**: batch, memory_limiter
- **Exporters**: OTLP (to Aspire Dashboard), debug (stdout)
- **Service**: `otel-collector.toytrip-staging.svc.cluster.local`

### Aspire Dashboard

- **Image**: `mcr.microsoft.com/dotnet/aspire-dashboard:9.0`
- **UI Port**: 18888 (HTTP)
- **OTLP Port**: 18889 (gRPC receiver)
- **Authentication**: Unsecured (dev mode) - can be changed to BrowserToken

## Installation

### Via ArgoCD (Recommended)

The chart is deployed via ArgoCD as part of the platform apps:

```yaml
# env/staging/platform/platform-observability-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-observability
  namespace: argocd
spec:
  source:
    path: helm-charts/platform-observability
  destination:
    namespace: toytrip-staging
```

### Manual Installation

```bash
# Install to staging namespace
helm install platform-observability ./helm-charts/platform-observability \
  --namespace toytrip-staging \
  --create-namespace

# Upgrade
helm upgrade platform-observability ./helm-charts/platform-observability \
  --namespace toytrip-staging
```

## Configuration

### Key Values

```yaml
# OpenTelemetry Collector
otelCollector:
  enabled: true
  replicas: 1
  service:
    grpcPort: 4317  # OTLP gRPC receiver
    httpPort: 4318  # OTLP HTTP receiver

# Aspire Dashboard
aspireDashboard:
  enabled: true
  replicas: 1
  service:
    uiPort: 18888   # Dashboard UI
    otlpPort: 18889 # OTLP receiver
  frontend:
    authMode: Unsecured  # or BrowserToken for token-based auth
```

### Authentication Modes

**Unsecured** (default for dev):
- No authentication required
- Dashboard accessible without login

**BrowserToken** (recommended for production):
- Generates a login token on startup
- Token displayed in pod logs
- Retrieve token: `kubectl logs -n toytrip-staging deployment/aspire-dashboard`

## Accessing the Dashboard

### Local Development (Port Forward)

```bash
# Forward dashboard UI port
kubectl port-forward -n toytrip-staging svc/aspire-dashboard 18888:18888

# Open browser
open http://localhost:18888
```

### From Application Services

Services send telemetry to the collector:

```yaml
env:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.toytrip-staging.svc.cluster.local:4317"
```

## Service Configuration

Application services need these environment variables:

```yaml
env:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.toytrip-staging.svc.cluster.local:4317"
  OTEL_SERVICE_NAME: "my-service"
  SERVICE_VERSION: "1.0.0"

# Kubernetes context (via Downward API)
envFieldRef:
  - name: K8S_NAMESPACE
    fieldPath: metadata.namespace
  - name: K8S_POD_NAME
    fieldPath: metadata.name
  - name: K8S_NODE_NAME
    fieldPath: spec.nodeName
```

## Customization

### Add Additional Exporters

To send telemetry to multiple backends (e.g., Azure Monitor):

```yaml
otelCollector:
  config:
    exporters:
      otlp:
        endpoint: aspire-dashboard:18889
        tls:
          insecure: true
      
      # Add Azure Monitor exporter
      azuremonitor:
        instrumentation_key: "${APPINSIGHTS_KEY}"
    
    service:
      pipelines:
        traces:
          exporters: [otlp, azuremonitor, debug]
```

### Scale Collector

For higher throughput:

```yaml
otelCollector:
  replicas: 3
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi
```

## Troubleshooting

### Check Collector Logs

```bash
kubectl logs -n toytrip-staging deployment/otel-collector
```

### Check Dashboard Logs

```bash
kubectl logs -n toytrip-staging deployment/aspire-dashboard
```

### Verify Services

```bash
kubectl get svc -n toytrip-staging
# Should show otel-collector and aspire-dashboard
```

### Test OTLP Endpoint

From a pod in the cluster:

```bash
# Test gRPC connectivity
kubectl run -n toytrip-staging test-curl --image=curlimages/curl --rm -it -- \
  curl -v http://otel-collector:4317
```

## Dashboard Features

- **Structured Logs**: View application logs with filtering and search
- **Traces**: Distributed tracing across services with span details
- **Metrics**: Time-series metrics with custom dimensions
- **Resources**: Service topology and resource metadata

## References

- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Aspire Dashboard](https://learn.microsoft.com/en-us/dotnet/aspire/fundamentals/dashboard/overview)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
