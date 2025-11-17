# Observability

## 1. Architecture Overview

All observability data flows through a centralized **OpenTelemetry (OTEL) Collector** deployed in the AKS cluster. Services instrument their code to emit logs, metrics, and traces using OpenTelemetry SDKs, sending telemetry to the collector which then routes data to multiple backends for storage, visualization, and alerting.

**Core Principle:** Unified telemetry pipeline with OpenTelemetry as the standard, enabling vendor-neutral instrumentation and flexible backend routing.

## 2. OpenTelemetry Collector Architecture

### 2.1 Deployment Model
* **OTEL Collector** deployed as a DaemonSet or Deployment in the `observability` namespace
* All application services push telemetry to the collector endpoint within the cluster
* Collector configured via ConfigMap for flexible routing and transformation
* Collector acts as central aggregation and routing point for all telemetry signals

### 2.2 Data Flow
```
Application Services → OTEL Collector → Multiple Backends:
                                      ├── Aspire Dashboard (local dev/quick inspection)
                                      ├── Azure Monitor for Prometheus (metrics)
                                      └── Azure Monitor Application Insights (logs & traces)
```

### 2.3 Configuration Strategy
* ConfigMap-based collector configuration for easy updates without redeployment
* Separate pipelines for logs, metrics, and traces
* Processors for batching, filtering, and attribute enrichment
* Exporters configured for each backend system

## 3. Application Instrumentation

### 3.1 OpenTelemetry SDK Integration
All services (toy, trip, addon, geo, story, agent, demo-*) instrumented with:
* **Logs:** Structured logging with OpenTelemetry context propagation
* **Metrics:** Counters, gauges, histograms for business and technical metrics
* **Traces:** Distributed tracing with spans for all significant operations

### 3.2 Auto-Instrumentation
Leverage OpenTelemetry auto-instrumentation libraries for:
* **FastAPI:** Automatic HTTP request/response tracing, metrics (request count, duration, status codes)
* **Azure SDK:** Blob Storage operations (upload, download, list), Cosmos DB queries (read, write, query execution time)
* **HTTP Clients:** Outbound HTTP calls with trace propagation
* **Service Bus:** Message send/receive operations with context propagation

Auto-instrumentation provides baseline observability with minimal code changes.

### 3.3 Context Propagation
* W3C Trace Context standard for trace propagation across service boundaries
* Correlation IDs maintained through synchronous REST calls and asynchronous message flows
* Trace context automatically injected into logs for correlation

## 4. Custom Dimensions and Attributes

### 4.1 User Context Dimensions
Add to all user-initiated operations:
* **user_id:** Principal OID from authentication token
* **user_role:** User role (standard user vs admin/System.Service)
* **is_admin:** Boolean flag for admin users (from roles claim)
* **toy_id:** Associated toy identifier when applicable
* **trip_id:** Associated trip identifier when applicable

### 4.2 Business Context Dimensions
Domain-specific attributes for business telemetry:
* **destination:** Geographic destination for trips
* **addon_type:** Type of add-on (accessory vs experience, specific category)
* **media_type:** Gallery image type (destination, fulfillment, live frame)
* **operation_type:** Business operation (register, create_trip, order_addon, view_gallery)

### 4.3 Technical Context Dimensions
Infrastructure and technical attributes:
* **service_name:** Microservice identifier (toy, trip, addon, etc.)
* **service_version:** Deployed version/commit SHA
* **namespace:** Kubernetes namespace
* **pod_name:** Pod identifier for troubleshooting
* **node_type:** Node pool/type (standard, memory-optimized, GPU)

## 5. Custom Metrics

### 5.1 Business Metrics
Domain-specific counters and gauges:
* **toys_viewed_total** (counter, dimensions: user_id, is_admin): Total toy profile views
* **trips_viewed_total** (counter, dimensions: user_id, trip_id, is_admin): Trip detail views
* **gallery_images_viewed_total** (counter, dimensions: trip_id, media_type, is_admin): Gallery image views
* **toys_registered_total** (counter, dimensions: is_admin): New toy registrations
* **trips_created_total** (counter, dimensions: user_id, destination): New trip creations
* **addons_ordered_total** (counter, dimensions: addon_type, is_admin): Add-on orders
* **live_sessions_active** (gauge): Current active live streaming sessions
* **story_compositions_requested_total** (counter): Story generation requests

### 5.2 Technical Metrics (Auto-Instrumented)
FastAPI and infrastructure metrics:
* **http_server_requests_total** (counter): HTTP request count by endpoint, method, status
* **http_server_request_duration_seconds** (histogram): Request latency distribution
* **http_server_active_requests** (gauge): Currently active requests
* **cosmos_operations_total** (counter): Database operations by type (read, write, query)
* **cosmos_request_units_consumed** (counter): RU consumption tracking
* **blob_operations_total** (counter): Blob storage operations (upload, download, list)
* **blob_operation_duration_seconds** (histogram): Blob operation latency

### 5.3 Queue and Background Metrics
Asynchronous processing metrics:
* **story_jobs_pending** (gauge): Pending story composition jobs (KEDA trigger)
* **media_generation_queue_depth** (gauge): Media generation queue size (KEDA trigger)
* **location_updates_per_second** (gauge): Location ping ingestion rate
* **websocket_connections_active** (gauge): Active WebSocket connections

## 6. Custom Spans and Traces

### 6.1 Business Operation Spans
High-level business transaction tracing:
* **toy.register:** Toy registration flow (validation, storage, avatar upload)
* **trip.create:** Trip creation (user validation, destination lookup, storage)
* **trip.gallery.upload:** Gallery image upload (blob storage, metadata update)
* **addon.order:** Add-on ordering (validation, fulfillment request, storage)
* **addon.fulfill:** Fulfillment processing (image generation, gallery update, notification)
* **story.compose:** Story generation (context gathering, AI invocation, storage)
* **geo.streamTick:** Location update broadcast (ingestion, WebSocket fan-out)

### 6.2 Span Attributes
Enrich spans with:
* User and role dimensions (user_id, is_admin)
* Business identifiers (toy_id, trip_id, addon_id)
* Operation outcomes (success/failure, error codes)
* Performance metrics (items processed, bytes transferred)

## 7. Aspire Dashboard

### 7.1 Purpose
Quick, local inspection of traces, metrics, and logs during development and troubleshooting.

### 7.2 Deployment
* Deployed in `observability` namespace
* Exposed via HTTPRoute for cluster access
* OTEL Collector configured to export to Aspire Dashboard endpoint
* Provides real-time view of distributed traces and telemetry

### 7.3 Use Cases
* Development-time debugging of trace flows
* Quick validation of instrumentation
* Troubleshooting production issues (temporary, not primary observability platform)

## 8. Azure Monitor for Prometheus

### 8.1 Architecture
* **Azure Monitor Workspace:** Managed Prometheus-compatible metrics storage
* **Remote Write:** OTEL Collector exports metrics in Prometheus format via remote write
* **Sidecar Authentication:** Azure-provided sidecar container handles Entra ID authentication

### 8.2 Authentication Flow
1. OTEL Collector sends metrics to sidecar proxy container (localhost)
2. Sidecar authenticates using Workload Identity (federated service account)
3. Sidecar forwards metrics to Azure Monitor workspace with valid Entra token
4. Metrics stored in Azure Monitor, queryable via PromQL

### 8.3 Sidecar Deployment
* Deploy Azure Monitor sidecar container alongside OTEL Collector
* Configure Workload Identity with "Monitoring Metrics Publisher" role on Data Collection Rule
* OTEL Collector remote_write endpoint points to sidecar (localhost:port)
* No direct secret management—uses AKS federated identity

### 8.4 Metric Retention
* Azure Monitor retains Prometheus metrics per configured retention policy
* Long-term storage and querying capabilities
* Integration with Azure Managed Grafana for visualization

## 9. Azure Managed Grafana

### 9.1 Integration
* Azure Managed Grafana instance connected to Azure Monitor workspace
* Pre-built dashboards for infrastructure and application metrics
* Custom dashboards for business metrics and KPIs

### 9.2 Key Dashboards
* **Service Health Dashboard:** Request rates, error rates, latency percentiles by service
* **Scaling Dashboard:** KEDA scaling events, pod replica counts, queue depths
* **Business Metrics Dashboard:** Toy views, trip views, gallery views, add-on orders (all with is_admin dimension)
* **Story Service Dashboard:** Story jobs pending, composition latency, memory usage
* **WebSocket Dashboard:** Active connections, message throughput, connection churn
* **Authentication Dashboard:** Token validation latency, auth failures by reason

### 9.3 Alerting
* Grafana alerts on critical metrics (error rate thresholds, queue depth limits, pod restart loops)
* Notification channels configured for operational team

## 10. Azure Monitor Application Insights

### 10.1 Purpose
Long-term storage and analysis of logs and distributed traces.

### 10.2 Data Flow
* OTEL Collector exports logs and traces to Application Insights
* Correlation between logs and traces via trace context
* Kusto Query Language (KQL) for advanced log analysis

### 10.3 Key Features
* **Distributed Tracing:** End-to-end trace visualization across microservices
* **Log Analytics:** Structured log search and analysis
* **Application Map:** Automatic service dependency mapping
* **Failure Analysis:** Exception tracking and impact analysis

## 11. AKS Monitoring and Cluster Observability

### 11.1 Container Insights
* Enable Azure Monitor Container Insights for AKS cluster
* Collects node and pod metrics (CPU, memory, disk, network)
* Container logs ingested to Log Analytics workspace
* Live data streaming for real-time troubleshooting

### 11.2 Networking Observability
* **Advanced Networking Observability:** Network flow logs and connection metrics from Azure CNI
* **Istio Ingress Gateway:** Envoy metrics and access logs
* **Service Mesh Telemetry:** Istio distributed tracing integration with OTEL

### 11.3 Cluster Metrics
* Node pool autoscaling events (Karpenter provisioning)
* KEDA scaling decisions and HPA metrics
* Pod scheduling and eviction events
* Resource quota and limit enforcement

## 12. Istio Service Mesh Integration

### 12.1 Distributed Tracing
* Istio Envoy proxies participate in distributed tracing
* Automatic trace context propagation through service mesh
* Ingress gateway spans included in end-to-end traces

### 12.2 Mesh Observability
* Istio metrics exported via OTEL Collector
* Service-to-service communication visibility
* mTLS connection metrics and certificate rotation tracking

### 12.3 Gateway Telemetry
* Ingress gateway request metrics (rate, latency, status codes)
* Traffic routing decisions and retry attempts
* TLS handshake metrics and connection pooling

## 13. Observability Operations

### 13.1 Deployment and Configuration
* OTEL Collector deployed via Helm chart
* ConfigMap for collector pipeline configuration
* Aspire Dashboard deployed as standalone service
* Azure resources (Monitor workspace, Grafana) provisioned via Infrastructure as Code

### 13.2 Security
* Workload Identity for all Azure service authentication
* No secrets in collector configuration (identity-based auth)
* RBAC for Grafana dashboard access
* Application Insights access controlled via Azure AD

### 13.3 Performance Considerations
* OTEL Collector batching and buffering to reduce network overhead
* Sampling strategies for high-volume traces (if needed)
* Metric aggregation and cardinality management
* Resource limits on collector pods to prevent cluster impact

### 13.4 Maintenance
* Regular review of custom metrics and dimensions for cardinality control
* Dashboard updates as new services and features are added
* Alert tuning based on operational experience
* Collector configuration updates via ConfigMap (rolling update)

## 14. Observability Goals

### 14.1 Performance Targets
* **Trace Collection:** <5ms overhead per instrumented operation
* **Metric Export:** <30s lag from generation to availability in Grafana
* **Log Ingestion:** <60s lag from generation to queryability in Application Insights
* **Dashboard Query:** <3s P95 response time for Grafana dashboards

### 14.2 Coverage Goals
* 100% of user-facing services instrumented with distributed tracing
* All critical business operations have custom spans
* All services emit standard health and performance metrics
* Admin operations clearly identified in all telemetry (is_admin dimension)

### 14.3 Operational Goals
* Mean time to detection (MTTD) <5 minutes for critical failures
* Mean time to diagnosis (MTTD) <15 minutes with observability data
* Zero blind spots in service-to-service communication flows
* Clear attribution of resource consumption by user type (admin vs standard)

---

**Note:** This document describes the observability architecture and design. Implementation details (SDK configuration, collector YAML, dashboard JSON) are maintained in service codebases and infrastructure repositories.
