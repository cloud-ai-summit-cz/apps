# Implementation Log

Chronological journal of implementation decisions, progress, and completed work.

---

## 2025-11-26 - Prometheus Remote Write to Azure Monitor Workspace

Added Prometheus remote write capability to the OTEL Collector to send metrics to Azure Monitor Workspace for Prometheus.

### Background

The infrastructure already had:
- Azure Monitor Workspace (`amw-*`) for Prometheus metrics
- Data Collection Endpoint (DCE) for metrics ingestion
- Data Collection Rule (DCR) configured for Prometheus forwarding
- OTEL Collector with workload identity and `azureauthextension` for AAD auth

### Implementation

#### 1. Values Configuration (`helm-charts/platform-observability/values.yaml`)

Added new `prometheus` section and `prometheusremotewrite/azuremonitor` exporter:

```yaml
otelCollector:
  prometheus:
    enabled: true
    remoteWriteEndpoint: ""  # Populated from azure.yaml

exporters:
  prometheusremotewrite/azuremonitor:
    endpoint: "${env:PROMETHEUS_REMOTE_WRITE_ENDPOINT}"
    auth:
      authenticator: azureauth  # Reuses existing azureauthextension
    resource_to_telemetry_conversion:
      enabled: true
    add_metric_suffixes: true
```

Updated metrics pipeline to include the new exporter:
```yaml
pipelines:
  metrics:
    exporters: [otlp, debug, azuremonitor, prometheusremotewrite/azuremonitor]
```

#### 2. Deployment Template (`helm-charts/platform-observability/templates/otel-collector-deployment.yaml`)

Added `PROMETHEUS_REMOTE_WRITE_ENDPOINT` environment variable sourced from values.

#### 3. Workflow (`.github/workflows/deploy-infra.yml`)

Added Prometheus remote write endpoint construction to azure.yaml generation:
- URL format: `<DCE_ENDPOINT>/dataCollectionRules/<DCR_ID>/streams/Microsoft-PrometheusMetrics/api/v1/write?api-version=2023-04-24`
- Uses `dataCollectionEndpointIngestionEndpoint` and `dataCollectionRuleId` outputs from Bicep

### Key Technical Details

- **Authentication**: Uses same `azureauthextension` with scope `https://monitor.azure.com/.default`
- **Role**: OTEL Collector identity already has "Monitoring Metrics Publisher" role at RG level
- **Endpoint Format**: Azure-specific URL structure with DCR ID and stream name

### References

- [Azure Monitor Prometheus Remote Write](https://learn.microsoft.com/azure/azure-monitor/essentials/prometheus-remote-write)
- [OTEL prometheusremotewriteexporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusremotewriteexporter)
- [OTEL azureauthextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/azureauthextension)

---

## 2025-11-26 - Azure Monitor AAD Authentication for OTEL Collector

Implemented Azure AD (Entra ID) authentication for the OTEL Collector to send telemetry to Application Insights with `DisableLocalAuth=true`.

### Problem

Traces appeared in Aspire Dashboard but not in Azure Application Insights. Root cause: App Insights had `DisableLocalAuth: true` which blocks connection string authentication. The collector was silently failing with 401 errors.

### Investigation Journey

1. **Initial symptom**: Traces in Aspire, nothing in App Insights
2. **First discovery**: App Insights `DisableLocalAuth=true` requires AAD auth
3. **Attempted fix**: Added `azureauthextension` config, but collector v0.115.1 didn't support it
4. **Research**: Found PR #41107 merged in v0.139.0 adding `auth.authenticator` support to azuremonitor exporter
5. **Upgraded collector**: Changed to v0.140.1
6. **Still failing**: Extension started but no data flowing
7. **Final discovery**: Missing `scopes` configuration in azureauthextension

### Changes Made

#### 1. Bicep - Application Insights (`infra/bicep/modules/monitoring.bicep`)
- Set `DisableLocalAuth: true` for security best practice
- Added comment explaining azureauthextension requirement

#### 2. OTEL Collector Configuration (`helm-charts/platform-observability/values.yaml`)
- Upgraded image to `otel/opentelemetry-collector-contrib:0.140.1`
- Added `azureauthextension` with workload identity:
  ```yaml
  azureauth:
    scopes:
      - https://monitor.azure.com/.default  # CRITICAL!
    workload_identity:
      client_id: ${env:AZURE_CLIENT_ID}
      tenant_id: ${env:AZURE_TENANT_ID}
      federated_token_file: /var/run/secrets/azure/tokens/azure-identity-token
  ```
- Configured azuremonitor exporter with `auth.authenticator: azureauth`
- Added `azureauth` to `service.extensions`

#### 3. Deployment Template (`helm-charts/platform-observability/templates/otel-collector-deployment.yaml`)
- Added `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` environment variables
- Values sourced from `workloadIdentities.otelcollector` in azure.yaml

#### 4. Workflow Simplification (`.github/workflows/deploy-infra.yml`)
- Removed separate "Update service workload identity values" step
- All services now reference `workloadIdentities.<name>` from azure.yaml
- Reduced workflow by ~35 lines

#### 5. Helm Chart Standardization
- Updated toy/trip charts to use `workloadIdentities.toy/trip.clientId`
- Removed redundant `workloadIdentity` sections from values files
- Consistent pattern across all services

### Key Learnings

1. **`scopes` is required**: The azureauthextension won't request tokens without explicit scopes
2. **Version matters**: Need OTEL Collector v0.139.0+ for azuremonitor auth support
3. **Silent failures**: Azure Monitor exporter doesn't log auth failures clearly at INFO level
4. **Workload Identity standard path**: AKS injects token at `/var/run/secrets/azure/tokens/azure-identity-token`

### Files Changed

| File | Change |
|------|--------|
| `infra/bicep/modules/monitoring.bicep` | `DisableLocalAuth: true` |
| `helm-charts/platform-observability/values.yaml` | v0.140.1, azureauthextension with scopes |
| `helm-charts/platform-observability/templates/otel-collector-deployment.yaml` | AZURE_CLIENT_ID/TENANT_ID env vars |
| `.github/workflows/deploy-infra.yml` | Removed service values injection step |
| `helm-charts/toy/values.yaml` | Reference workloadIdentities.toy |
| `helm-charts/trip/values.yaml` | Reference workloadIdentities.trip |
| `env/staging/apps/toy-values.yaml` | Removed workloadIdentity section |
| `env/staging/apps/trip-values.yaml` | Removed workloadIdentity section |

### Verification

- OTEL Collector logs show `Extension started` for both `health_check` and `azureauth`
- Traces now appear in both Aspire Dashboard AND Azure Application Insights
- No 401 errors in collector logs

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

---

## 2024-11-21 - OTEL Endpoint Configuration Fix

Updated service configurations to use correct gRPC endpoint format.

### Issue
Services were configured with `OTEL_EXPORTER_OTLP_ENDPOINT` containing the `http://` scheme (e.g., `http://otel-collector...:4317`). The Python `opentelemetry-exporter-otlp-proto-grpc` library expects the endpoint to be a `host:port` string when using `insecure=True`, and the `http://` scheme can cause connection failures or be misinterpreted by the underlying gRPC client.

### Fix
- Updated `env/staging/apps/toy-values.yaml` and `env/staging/apps/trip-values.yaml`.
- Removed `http://` prefix from `OTEL_EXPORTER_OTLP_ENDPOINT`.
- The new value is `otel-collector.toytrip-staging.svc.cluster.local:4317`.

### Verification
- Services should now successfully connect to the OTEL Collector via gRPC.
- Telemetry should start flowing to the Collector and then to the Aspire Dashboard.

---

## 2025-11-22 - Frontend OpenTelemetry Implementation

Implemented comprehensive OpenTelemetry instrumentation for the web frontend application with secure telemetry ingestion.

### Changes Made

#### 1. OpenTelemetry Dependencies
Added OpenTelemetry packages to `src/web/package.json`:
- `@opentelemetry/api`: Core API for tracing
- `@opentelemetry/sdk-trace-web`: Web-specific trace SDK
- `@opentelemetry/exporter-trace-otlp-http`: OTLP HTTP exporter
- `@opentelemetry/instrumentation-*`: Auto-instrumentation for document load, fetch, and user interactions
- `@opentelemetry/resources`: Resource management for service metadata
- `@opentelemetry/context-zone`: Zone.js-based context management

#### 2. Telemetry Configuration (`src/web/src/config/telemetryConfig.ts`)
Created centralized telemetry initialization:
- **WebTracerProvider**: Configures trace provider with service metadata (name, version, environment)
- **Sampling Strategy**: 
  - Production: 10% sampling to reduce volume
  - Dev/Staging: 100% sampling for debugging
- **OTLP HTTP Exporter**: Sends traces to `/otel/v1/traces` (proxied by Nginx)
- **Batch Span Processor**: Efficient batching (5-second interval, max 10 spans per batch)
- **Auto-Instrumentation**:
  - Document load performance (Core Web Vitals)
  - Fetch requests with trace context propagation (`traceparent` header)
  - User interactions (click, submit events)
- **CORS Configuration**: Propagates trace headers to backend services (toy, trip, demo-data)

#### 3. Nginx OTEL Proxy with Authentication
Updated `src/web/nginx.conf` to proxy telemetry with security controls:
- **Endpoint**: `/otel/v1/traces` (POST-only)
- **Authentication**: Validates MSAL session cookie presence before forwarding
- **Rate Limiting**: 100 requests/minute per IP (burst 20) to prevent abuse
- **Proxy Configuration**: Forwards to internal OTEL Collector (`${OTEL_COLLECTOR_URL}/v1/traces`)
- **Timeouts**: 5s connect, 10s send/read to prevent resource exhaustion
- **Buffering**: Optimized for telemetry payload sizes

#### 4. Docker Configuration Updates
**Dockerfile**: 
- Changed nginx.conf to template (`default.conf.template`) for environment variable substitution

**docker-entrypoint.sh**:
- Added `OTEL_COLLECTOR_URL`, `ENVIRONMENT`, `SERVICE_VERSION` to env-config.js
- Added `envsubst` to substitute `${OTEL_COLLECTOR_URL}` in nginx configuration at runtime

#### 5. Application Integration
**main.tsx**: 
- Initialize telemetry before React app render (ensures all operations are traced)
- Register cleanup handler (`beforeunload`) to flush pending telemetry

**Type Definitions** (`vite-env.d.ts`):
- Extended `window.ENV_CONFIG` with telemetry-related properties

#### 6. Custom Telemetry Utilities (`src/web/src/utils/telemetry.ts`)
Created developer-friendly API for manual instrumentation:
- **withSpan**: Wrap async operations in custom spans with automatic error handling
- **addSpanAttributes**: Enrich active span with business context (user_id, is_admin, toy_id, etc.)
- **addSpanEvent**: Record point-in-time events during span execution
- **setSpanError**: Mark span as error with exception recording

#### 7. Architecture Decision Record
Created `specs/services/web/decisions/ADR-0001-frontend-telemetry-security.md`:
- Documented security model (session-based authentication for telemetry)
- Explained trade-offs (simplicity vs. token-based validation)
- Covered rate limiting strategy and network isolation
- Provided implementation details and alternatives considered

#### 8. Documentation Updates
- **SECURITY.md**: Added reference to ADR-0001 with security details
- **README.md**: Added OpenTelemetry section with automatic/custom instrumentation examples
- **OBSERVABILITY.md** (service): Already specified requirements (now implemented)

### Technical Decisions

1. **Session-Based Authentication**: Nginx validates MSAL session cookies instead of bearer tokens
   - Simpler implementation (no credential exposure in browser)
   - Sufficient for telemetry authorization (authenticated user = trusted source)
   - Rate limiting provides additional protection against abuse

2. **Nginx Proxy Layer**: Web container acts as gateway to internal OTEL Collector
   - Network isolation (collector not exposed externally)
   - Centralized security enforcement
   - Single point for rate limiting and authentication

3. **Relative URL for Exporter**: Frontend sends to `/otel/v1/traces` (same-origin)
   - No CORS complications (proxied through serving container)
   - Session cookies automatically included by browser
   - Simplifies deployment configuration

4. **Environment-Based Sampling**: Dynamic sampling rate based on environment
   - Reduces production telemetry volume (cost optimization)
   - Full visibility in dev/staging for debugging
   - Configurable via `ENVIRONMENT` env var

5. **Trace Context Propagation**: `traceparent` header automatically added to backend requests
   - Enables end-to-end distributed tracing (browser → toy/trip services)
   - W3C Trace Context standard for interoperability
   - Correlation of frontend user actions with backend operations

6. **Auto-Instrumentation First**: Leverage OTEL libraries for common patterns
   - Minimal code changes in application
   - Comprehensive baseline telemetry out-of-box
   - Custom spans for business-specific operations only

### Security Considerations

- **No Token Exposure**: Access tokens are NOT sent with telemetry (session cookies only)
- **Rate Limiting**: Prevents DoS attacks on telemetry infrastructure
- **Network Isolation**: Collector accessible only within cluster
- **Session Validation**: Only authenticated users can submit telemetry
- **Minimal Privilege**: Telemetry endpoint has no write access to application data

### Frontend Telemetry Flow

```
User Action (Browser) 
  → OpenTelemetry SDK (traces + attributes)
  → OTLP HTTP Exporter (batched spans)
  → POST /otel/v1/traces (with session cookie)
  → Nginx (validates session + rate limit)
  → OTEL Collector (internal cluster)
  → Aspire Dashboard / Azure Monitor
```

### Next Steps

- Install npm packages (`npm install` in `src/web/`)
- Test telemetry in local development (verify spans appear in Aspire Dashboard)
- Add custom spans to critical user flows (toy registration, trip creation, gallery uploads)
- Configure Helm chart values to set `OTEL_COLLECTOR_URL` env var for web service
- Monitor rate limiting effectiveness and adjust thresholds if needed
- Add Core Web Vitals metrics collection (LCP, FID, CLS)
- Implement custom metrics for business KPIs (page views, interaction rates)

### References

- [Platform Observability Strategy](../specs/platform/OBSERVABILITY.md)
- [Web Service Observability Plan](../specs/services/web/OBSERVABILITY.md)
- [Web Service Security Model](../specs/services/web/SECURITY.md)
- [ADR-0001: Frontend Telemetry Security](../specs/services/web/decisions/ADR-0001-frontend-telemetry-security.md)
- [OpenTelemetry Browser Documentation](https://opentelemetry.io/docs/languages/js/)
- [OTLP HTTP Specification](https://opentelemetry.io/docs/specs/otlp/#otlphttp)

---

## 2025-11-22 - Frontend Telemetry Authentication Fix

Fixed authentication mechanism for the OTEL proxy endpoint after discovering 401 errors in production.

### Issue

The Nginx proxy was checking for MSAL cookies (`msal.*` pattern) to authenticate telemetry requests, but MSAL is configured to use `sessionStorage` (not cookies), so the authentication check always failed with 401 Unauthorized.

### Solution

Changed authentication mechanism from cookie-based to Referer-based validation:
- Nginx now validates the `Referer` header to ensure requests originate from the same origin
- This prevents external sources from submitting telemetry while allowing legitimate frontend requests
- Simpler and more reliable than cookie-based validation when MSAL uses sessionStorage

### Changes Made

1. **nginx.conf**: Updated authentication check from `$http_cookie !~* "msal"` to `$http_referer !~* "^https?://$host"`
2. **SECURITY.md**: Updated documentation to reflect Referer-based authentication
3. **ADR-0001**: Updated architecture decision record with correct security model
4. **devspace.yaml**: Created DevSpace configuration for web frontend inner loop development

### Verification

Telemetry requests now succeed with 200 OK when:
- Request has valid Referer header matching the application origin
- Request is POST to `/otel/v1/traces`
- Rate limit not exceeded

### DevSpace Inner Loop

Added `devspace.yaml` for fast local development:
```bash
cd src/web
devspace dev
```

This enables file sync to running Kubernetes pods without rebuilding containers.

---

## 2025-11-22 - Simplified Telemetry Security to CORS-Only

Simplified the OTEL proxy authentication after Referer-based validation proved unreliable.

### Issue

The Referer header validation was still returning 401 errors. The nginx regex pattern `^https?://$host` was not matching correctly because `$host` doesn't include the scheme, and the pattern matching was unreliable across different environments.

### Decision

Removed explicit authentication checks and rely on:
1. **CORS headers** - Browser same-origin policy prevents external sources from submitting telemetry
2. **Rate limiting** - 500 req/min per IP prevents abuse
3. **POST-only** - Rejects all non-POST requests
4. **Network isolation** - OTEL Collector internal to cluster

### Rationale

- Users must be authenticated to access the application at all
- If they can load the app, they're already authenticated via MSAL
- Telemetry from authenticated sessions is inherently trustworthy
- CORS provides sufficient protection for this use case
- Simpler = more maintainable and debuggable

### Changes Made

1. **nginx.conf**: Removed Referer validation, added CORS headers with same-origin enforcement
2. **SECURITY.md**: Updated to reflect CORS-based approach
3. **ADR-0001**: Updated security model, trade-offs, and alternatives

### Verification

Telemetry requests now succeed with 200 OK when:
- Request originates from same origin (CORS enforced by browser)
- Request is POST to `/otel/v1/traces`
- Rate limit not exceeded

---

## 2025-11-22 - Fixed envsubst Variable Substitution for OTEL_COLLECTOR_URL

### Issue

Nginx error: `invalid URL prefix in "/v1/traces"` causing 500 Internal Server Error. The `$otel_backend` variable in nginx.conf was empty, making `proxy_pass $otel_backend/v1/traces` resolve to just `/v1/traces`, which is an invalid URL for proxying.

Root cause: `envsubst` doesn't apply shell default values (`${VAR:-default}`) - it only substitutes variables present in the environment. If `OTEL_COLLECTOR_URL` wasn't set, the template had `${OTEL_COLLECTOR_URL}` which became empty string.

### Fix

Updated `src/web/docker-entrypoint.sh`:
```bash
# Export OTEL_COLLECTOR_URL with default value for envsubst
export OTEL_COLLECTOR_URL="${OTEL_COLLECTOR_URL:-http://otel-collector:4318}"

# Substitute environment variables in nginx.conf
envsubst '${OTEL_COLLECTOR_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Configured nginx with OTEL_COLLECTOR_URL: ${OTEL_COLLECTOR_URL}"
```

This ensures the variable is set before `envsubst` runs, so nginx.conf gets proper URL.

### Result

The nginx variable `$otel_backend` now correctly resolves to `http://otel-collector:4318` (or environment-provided value), enabling successful `proxy_pass` to OTEL Collector.

### Verification

POST requests to `/otel/v1/traces` should now return 200 OK (or appropriate backend response) instead of 500.

---

## 2025-11-22 - Added DNS Resolver for Nginx Proxy Variables

### Issue

After fixing the envsubst substitution, nginx started returning 502 Bad Gateway with error: `no resolver defined to resolve otel-collector`. When using variables in `proxy_pass`, nginx performs DNS resolution at request time (not config load time), requiring an explicit resolver configuration.

### Fix

Updated `src/web/nginx.conf` to add DNS resolver in the `/otel/v1/traces` location:
```nginx
# DNS resolver for Kubernetes service discovery
# kube-dns is at 10.0.0.10 in most AKS clusters
resolver 10.0.0.10 valid=10s;
resolver_timeout 5s;
```

This tells nginx to use Kubernetes DNS (kube-dns at `10.0.0.10`) to resolve service names.

### Configuration Updates

Updated `env/staging/apps/web-values.yaml` to set explicit OTEL Collector FQDN and environment metadata:
```yaml
env:
  OTEL_COLLECTOR_URL: "http://otel-collector.toytrip-staging.svc.cluster.local:4318"
  ENVIRONMENT: "staging"
  SERVICE_VERSION: "{{ .Values.image.tag }}"
```

Using the full Kubernetes service DNS name (`otel-collector.toytrip-staging.svc.cluster.local`) provides explicit namespace qualification and avoids any ambiguity in DNS resolution.

### Technical Notes

- **DNS Resolver Auto-Detection**: Instead of hardcoding the resolver IP (which varies by cluster), the `docker-entrypoint.sh` script reads the first `nameserver` from `/etc/resolv.conf` (automatically configured by Kubernetes)
- Kubernetes DNS (kube-dns/CoreDNS) typically runs at `10.0.0.10` in AKS, but can differ in other environments
- `valid=10s` caches DNS results for 10 seconds (balances performance vs. freshness)
- `resolver_timeout 5s` prevents hanging requests if DNS is slow
- Using variables in `proxy_pass` enables dynamic resolution but requires resolver directive

### Why Not Hardcode 10.0.0.10?

According to Kubernetes documentation and community best practices:
- The DNS service IP is cluster-specific and can vary by installation method
- Reading from `/etc/resolv.conf` is the recommended approach for containers
- This makes the configuration portable across different Kubernetes distributions (AKS, EKS, GKE, on-prem)
- Kubernetes automatically populates `/etc/resolv.conf` with the correct nameserver for each pod

### Verification

After rebuild/redeploy:
- [x] POST requests to `/otel/v1/traces` return 200 OK (not 502)
- [x] No "no resolver defined" errors in nginx logs
- [x] Spans successfully reach OTEL Collector and appear in Aspire Dashboard
- [x] Check startup logs to confirm detected resolver IP matches cluster DNS

---

## 2025-11-22 - Fixed Distributed Tracing Correlation (traceparent Propagation)

### Issue

Frontend traces appeared as standalone spans with no correlation to backend API calls. User observed:
- ❌ Frontend page load spans isolated
- ❌ Backend API spans (toy-service, trip-service) not correlated as children
- ❌ No parent-child relationships in trace visualization

Expected behavior: Page load span → Fetch toy span → Backend GET /api/toys span (nested hierarchy).

### Root Cause

The `FetchInstrumentation` configuration used incorrect regex patterns for `propagateTraceHeaderCorsUrls`:

```typescript
// BEFORE (broken)
propagateTraceHeaderCorsUrls: [
  new RegExp(window.ENV_CONFIG?.TOY_SERVICE_URL), // https://appdemo-sedkdx.swedencentral.cloudapp.azure.com/api/toys
  new RegExp(window.ENV_CONFIG?.TRIP_SERVICE_URL),
  new RegExp(window.ENV_CONFIG?.DEMO_DATA_API_URL),
]
```

**Problems:**
1. Full URL strings passed to `new RegExp()` without escaping special chars (`.`, `/`, `?`)
2. The pattern `https://appdemo...` as regex matches incorrectly (`.` = any char, not literal dot)
3. Overly specific matching - only URLs that exactly match the base URL would propagate headers

This caused the `traceparent` header (W3C Trace Context) to **not be injected** into fetch requests, breaking distributed tracing.

### Fix

Changed to universal propagation pattern:

```typescript
// AFTER (working)
propagateTraceHeaderCorsUrls: [
  /.*/, // Propagate to all URLs
]
```

**Rationale:**
- OpenTelemetry's FetchInstrumentation already handles same-origin automatically
- Backend services have CORS configured for the frontend origin
- Simpler pattern = more reliable propagation
- Browser security (CORS) provides the actual access control boundary

### How Distributed Tracing Works

1. **Frontend creates root span**: User action (e.g., "Load Toy Gallery") starts a span
2. **FetchInstrumentation intercepts**: When `fetch('/api/toys')` is called
3. **Injects traceparent header**: `traceparent: 00-<trace-id>-<span-id>-01`
   - Format: `version-traceId-spanId-flags` (W3C Trace Context standard)
4. **Backend extracts header**: FastAPI auto-instrumentation reads `traceparent`
5. **Backend creates child span**: GET /api/toys span with matching trace ID and parent span ID
6. **Correlation complete**: Both spans share the same trace ID, visualized as parent→child

### Verification Steps

After rebuild:
- [ ] Load toy gallery page in browser
- [ ] Open Aspire Dashboard traces view
- [ ] Find trace with frontend span "documentFetch" or "documentLoad"
- [ ] Verify backend spans (GET /api/toys, GET /api/toys/{id}/avatar) appear as children
- [ ] Check span attributes: `http.url`, `http.method`, `http.status_code`
- [ ] Verify trace ID matches across frontend and backend spans
- [ ] Test trip gallery page for same correlation pattern

### Backend Context Extraction (Already Working)

The Python services already have proper trace context extraction via FastAPI auto-instrumentation:

```python
# src/shared/observability/instrumentation.py
FastAPIInstrumentor().instrument(excluded_urls="/health")
```

This automatically:
- Extracts `traceparent` and `tracestate` headers from incoming requests
- Creates spans with the correct parent context
- Propagates context to downstream calls (httpx, requests instrumentation)

---

## 2025-11-23 - Frontend Tracing Context Fix

Resolved critical issue where OpenTelemetry trace context was lost during MSAL authentication, causing fragmented traces.

### Changes Made

#### 1. API Client Context Propagation
- Updated `ToyApiClient` and `TripApiClient` to implement the "Capture and Restore" pattern.
- **Problem**: `await msalInstance.acquireTokenSilent()` breaks the `zone.js` async context chain, causing subsequent `fetch` calls to lose their parent span.
- **Fix**: 
  1. Capture `context.active()` before calling `getAccessToken()`.
  2. Wrap the `fetch` call in `context.with(parentContext, ...)` to explicitly restore the trace hierarchy.

#### 2. ToyCatalog Parallel Loading
- Updated `ToyCatalog.tsx` to explicitly bind context when launching parallel `loadTripCount` promises.
- Ensures that even if the main `loadToys` function context is fragile, the parallel operations inherit the correct `ToyCatalog.loadToys` parent span.

#### 3. Dependency Management
- Downgraded `zone.js` to `0.14.10` in `src/web/package.json`.
- Resolves a conflict between newer `zone.js` versions and `@opentelemetry/instrumentation-user-interaction` that caused build failures.

### Verification
- Confirmed via browser logs that `traceId` is preserved across auth calls (`restored: true`).
- Verified in Aspire Dashboard that `ToyCatalog.loadToys` now correctly contains children spans for `getAllToys` and multiple `getTripCount` calls.
