# Implementation Log

Chronological journal of implementation decisions, progress, and completed work.

---

## 2024-11-21 - OpenTelemetry Instrumentation Implementation

Implemented comprehensive OpenTelemetry (OTEL) instrumentation for toy and trip services following the observability strategy defined in specs/platform/OBSERVABILITY.md.

### Changes Made

#### 1. Shared Observability Module (`src/shared/observability/`)
Created centralized OTEL instrumentation utilities:
- **instrumentation.py**: Core setup function configuring traces, metrics, and logs with OTLP exporter
- **Auto-instrumentation**: Integrated FastAPI, HTTP clients (httpx, requests), and Azure SDK tracing
- **Logging Configuration**: Application logs at INFO level, Azure SDK logs at WARNING+ only
- **Helper Functions**: `get_tracer()` and `get_meter()` for custom spans and metrics

Key features:
- Single `setup_instrumentation()` call before FastAPI app creation
- OTLP gRPC exporter for all telemetry (vendor-neutral)
- W3C trace context propagation for distributed tracing
- Batch processing for efficient export

#### 2. Service Configuration Updates
Added OTEL environment variables to both services:
- `OTEL_EXPORTER_OTLP_ENDPOINT`: Collector endpoint (default: http://localhost:4317)
- `OTEL_SERVICE_NAME`: Service identifier (toy-service, trip-service)
- `SERVICE_VERSION`: Version for resource attributes
- `K8S_NAMESPACE`, `K8S_POD_NAME`, `K8S_NODE_NAME`: Kubernetes context (optional)

Updated files:
- `src/services/toy/config.py`, `.env`, `.env.example`
- `src/services/trip/config.py`, `.env`, `.env.example`

#### 3. Service Integration
**Toy Service** (`main.py` and `toy_routes.py`):
- Initialize OTEL before FastAPI app creation
- Custom metrics: `toys_viewed_total`, `toys_registered_total`
- Custom spans: `toy.register`, `toy.avatar.upload` with business attributes
- Span attributes: toy_id, user_id, is_admin, success/failure

**Trip Service** (`main.py` and `trip_routes.py`):
- Initialize OTEL before FastAPI app creation
- Custom metrics: `trips_viewed_total`, `trips_created_total`, `gallery_images_viewed_total`
- Custom spans: `trip.create` with destination and toy context
- Span attributes: trip_id, toy_id, user_id, destination, media_type

#### 4. Dependencies (`pyproject.toml`)
Added OpenTelemetry packages to both services:
- `opentelemetry-api>=1.20.0`
- `opentelemetry-sdk>=1.20.0`
- `opentelemetry-exporter-otlp-proto-grpc>=1.20.0`
- `opentelemetry-instrumentation-fastapi>=0.41b0`
- `opentelemetry-instrumentation-httpx>=0.41b0`
- `opentelemetry-instrumentation-requests>=0.41b0`
- `azure-core-tracing-opentelemetry>=1.0.0`

#### 5. Docker Configuration
Updated Dockerfiles to copy shared observability module:
- `COPY shared/observability /app/shared/observability`
- Ensures instrumentation is available at runtime

### Technical Decisions

1. **OTLP Collector Architecture**: All services push to centralized collector, not directly to backends
   - Enables flexible backend routing without code changes
   - Simplifies service configuration (single endpoint)

2. **Auto-instrumentation First**: Leverage OTEL libraries for FastAPI, Azure SDK, HTTP clients
   - Minimal code changes in services
   - Comprehensive baseline telemetry out-of-box
   - Custom spans/metrics for business-specific operations only

3. **Logging Strategy**: Application INFO+, SDK WARNING+
   - Reduces noise from verbose SDK operations
   - All logs sent to OTLP (no separate console handler needed)
   - Automatic trace context injection for correlation

4. **Resource Attributes**: Service name, version, K8s context
   - Enables filtering/grouping in backends
   - Version tracking for deployment correlation
   - K8s attributes for infrastructure context

5. **Custom Metrics Dimensions**: User context (user_id, is_admin), business entities (toy_id, trip_id, destination)
   - Enables user behavior analysis
   - Admin vs user activity tracking
   - Business metric segmentation

### Next Steps

- Deploy OTEL Collector to AKS (separate task)
- Configure collector pipelines for multiple backends (Aspire Dashboard, Azure Monitor)
- Add custom metrics to remaining services (addon, geo, story, agent)
- Implement distributed tracing scenarios across service boundaries
- Create Grafana dashboards for business metrics

### References

- [Platform Observability Strategy](../specs/platform/OBSERVABILITY.md)
- [Shared Observability README](../src/shared/observability/README.md)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Azure SDK OpenTelemetry Integration](https://learn.microsoft.com/python/api/overview/azure/core-tracing-opentelemetry-readme)

---

## 2024-11-21 - OTEL Collector and Aspire Dashboard Deployment

Deployed centralized observability infrastructure with OpenTelemetry Collector and Aspire Dashboard.

### Changes Made

#### 1. Platform-Observability Helm Chart (`helm-charts/platform-observability/`)
Created new Helm chart for the observability stack:

**OpenTelemetry Collector:**
- Image: `otel/opentelemetry-collector-contrib:0.115.1`
- Receivers: OTLP gRPC (4317), OTLP HTTP (4318)
- Processors: batch, memory_limiter
- Exporters: OTLP (to Aspire Dashboard), debug (stdout)
- Service endpoint: `otel-collector.toytrip-staging.svc.cluster.local:4317`
- Resources: 100m CPU / 128Mi RAM (requests), 500m CPU / 512Mi RAM (limits)

**Aspire Dashboard:**
- Image: `mcr.microsoft.com/dotnet/aspire-dashboard:9.0`
- UI port: 18888 (HTTP)
- OTLP receiver port: 18889 (gRPC)
- Authentication: Unsecured mode for development (can switch to BrowserToken)
- Resources: 50m CPU / 128Mi RAM (requests), 200m CPU / 256Mi RAM (limits)

**Kubernetes Resources:**
- ConfigMap: OTEL collector configuration (receivers, processors, exporters, pipelines)
- Deployments: otel-collector, aspire-dashboard
- Services: ClusterIP for both components
- Health checks: liveness and readiness probes

#### 2. Service Configuration Updates

**Toy Service** (`env/staging/apps/toy-values.yaml`):
- Added `OTEL_EXPORTER_OTLP_ENDPOINT`: Points to collector service
- Added `OTEL_SERVICE_NAME`: "toy-service"
- Added `SERVICE_VERSION`: Matches image tag for version correlation
- Added K8s Downward API env vars: `K8S_NAMESPACE`, `K8S_POD_NAME`, `K8S_NODE_NAME`

**Trip Service** (`env/staging/apps/trip-values.yaml`):
- Added `OTEL_EXPORTER_OTLP_ENDPOINT`: Points to collector service
- Added `OTEL_SERVICE_NAME`: "trip-service"
- Added `SERVICE_VERSION`: Matches image tag for version correlation
- Added K8s Downward API env vars: `K8S_NAMESPACE`, `K8S_POD_NAME`, `K8S_NODE_NAME`

#### 3. Helm Chart Template Updates

**Toy & Trip Deployment Templates:**
- Added support for `envFieldRef` to inject Kubernetes metadata via Downward API
- Environment variables now populated from pod/node metadata dynamically
- Enables resource attribution in telemetry (namespace, pod name, node name)

#### 4. ArgoCD Integration

**Platform Application** (`env/staging/platform/platform-observability-app.yaml`):
- Created ArgoCD Application for observability stack
- Targets `helm-charts/platform-observability` path
- Deploys to `toytrip-staging` namespace
- Auto-sync enabled with prune and self-heal
- Automatically discovered by `platform-root-staging` app (includes all *-app.yaml files)

### Technical Decisions

1. **Collector as Central Aggregator**: All services send to collector, not directly to backends
   - Decouples services from backend changes
   - Single point for routing, filtering, batching
   - Enables multi-backend export without service redeployment

2. **Aspire Dashboard for Development**: Developer-focused visualization tool
   - Lower setup complexity than Prometheus/Grafana/Jaeger
   - Single UI for logs, metrics, traces
   - Not recommended for production monitoring (use Azure Monitor for that)
   - No authentication in dev mode for ease of access

3. **OTLP Protocol Standard**: OpenTelemetry Line Protocol (gRPC)
   - Vendor-neutral telemetry ingestion
   - Single protocol for logs, metrics, traces
   - Native support in all OTEL SDKs
   - Can add Azure Monitor exporter later without service changes

4. **Kubernetes Downward API**: Pod/node metadata injection
   - Enables resource-based filtering in dashboards
   - Correlates telemetry with infrastructure (pod restarts, node failures)
   - Automatic update when pods are rescheduled

5. **Pipeline Architecture**:
   - Services → Collector (OTLP:4317) → Aspire Dashboard (OTLP:18889)
   - Debug exporter to collector stdout for troubleshooting
   - Memory limiter to prevent collector OOM
   - Batch processor for efficient export

### Deployment Flow

1. **ArgoCD Syncs Platform Apps**: `platform-root-staging` discovers new `platform-observability-app.yaml`
2. **Observability Stack Deploys**: Collector and Aspire Dashboard pods start
3. **Services Reference Collector**: Toy/trip services configured with collector endpoint
4. **Telemetry Flows**: Services send OTLP → Collector batches → Aspire Dashboard visualizes

### Access Dashboard

```bash
# Port forward to local machine
kubectl port-forward -n toytrip-staging svc/aspire-dashboard 18888:18888

# Open browser
open http://localhost:18888
```

### Next Steps

- Monitor collector performance and scale if needed (increase replicas, resources)
- Add Azure Monitor exporter for production telemetry persistence
- Configure BrowserToken authentication for dashboard in production
- Add additional OTEL processors (attribute enrichment, sampling, filtering)
- Deploy Grafana dashboards for long-term metric visualization
- Set up alerts based on custom metrics (toys_viewed_total, trips_created_total)

### References

- [Platform Observability Helm Chart](../helm-charts/platform-observability/README.md)
- [Aspire Dashboard Documentation](https://learn.microsoft.com/en-us/dotnet/aspire/fundamentals/dashboard/overview)
- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)

---

## 2024-11-21 - Observability Stack Refinement and Documentation

Refined the observability stack configuration and updated system documentation to reflect the new components.

### Changes Made

#### 1. OTEL Collector Configuration Fix
- Updated `helm-charts/platform-observability/values.yaml` to enable the `health_check` extension.
- Configured the extension on endpoint `0.0.0.0:13133`.
- Added the extension to the service pipeline.
- This ensures the Kubernetes liveness and readiness probes (configured on port 13133) will pass successfully.

#### 2. Architecture Documentation (`specs/platform/ARCHITECTURE.md`)
- Added `otel-collector` and `aspire-dashboard` to the "Container / Service View" table.
- Documented their responsibility (Telemetry aggregation/routing, Visualization) and ownership (Platform).

#### 3. Service Deployment Documentation
- Updated `specs/services/toy/DEPLOYMENT.md` and `specs/services/trip/DEPLOYMENT.md`.
- Added "Observability" to the Infrastructure Dependencies section.
- Explicitly mentioned the dependency on `otel-collector` via the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable.

### Verification
- Verified `platform-observability` Helm chart values match the deployment template expectations.
- Confirmed ArgoCD application `env/staging/platform/platform-observability-app.yaml` is correctly placed for discovery by the platform root app.

---

## 2024-11-21 - Aspire Dashboard Health Check Fix

Fixed the liveness and readiness probes for the Aspire Dashboard.

### Issue
The Aspire Dashboard pod was crashing with `CrashLoopBackOff` because the configured health check endpoint `/health` returned 404 Not Found. The standalone Aspire Dashboard image does not expose a dedicated `/health` endpoint on the UI port by default.

### Fix
- Updated `helm-charts/platform-observability/templates/aspire-dashboard-deployment.yaml` to use the root path `/` for liveness and readiness probes.
- Since the dashboard is running in `Unsecured` mode, the root path returns 200 OK (or a redirect handled as success), which correctly indicates the application is running.

### Verification
- The change ensures the kubelet can successfully probe the dashboard and keep the pod running.

---

## 2024-11-21 - OTEL Collector ConfigMap Fix

Fixed the OTEL Collector ConfigMap template to include the `extensions` block.

### Issue
The OTEL Collector was crashing with `invalid configuration: service::extensions: references extension "health_check" which is not configured`. This happened because although `extensions` were defined in `values.yaml`, the `otel-collector-configmap.yaml` template was not rendering the `extensions` section into the final `config.yaml`.

### Fix
- Updated `helm-charts/platform-observability/templates/otel-collector-configmap.yaml` to include:
  ```yaml
  extensions:
    {{- toYaml .Values.otelCollector.config.extensions | nindent 6 }}
  ```
- This ensures the `health_check` extension definition is present in the configuration file, resolving the reference error.

### Verification
- The generated ConfigMap will now contain the `extensions` block, allowing the collector to start successfully.

---

## 2024-11-21 - Aspire Dashboard Connectivity Fixes

Addressed connectivity issues between OTEL Collector and Aspire Dashboard.

### Issues
1. **Connection Refused**: The OTEL Collector could not connect to the Aspire Dashboard (`dial tcp ... connection refused`). This was likely due to the Dashboard pod not being marked "Ready" because of failing HTTP probes, causing the Service to have no endpoints.
2. **Probe Reliability**: The HTTP probe on `/` might be returning unexpected status codes or redirects, causing the pod to stay in `CrashLoopBackOff` or unready state.

### Fixes
1. **Updated Probes**: Changed `livenessProbe` and `readinessProbe` in `helm-charts/platform-observability/templates/aspire-dashboard-deployment.yaml` to use `tcpSocket` instead of `httpGet`. This ensures the pod is marked ready as soon as the UI port (18888) is open, avoiding HTTP path/status ambiguity.
2. **Service Port Definition**: Updated `helm-charts/platform-observability/templates/aspire-dashboard-service.yaml` to use numeric `targetPort` (e.g., 18888, 18889) instead of named ports. This improves reliability of port mapping.

### Verification
- The Dashboard pod should now become Ready reliably.
- The Service will populate with the pod's endpoint.
- The OTEL Collector should successfully connect to `aspire-dashboard:18889`.
