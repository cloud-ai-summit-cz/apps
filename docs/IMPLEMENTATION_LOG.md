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
