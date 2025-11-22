# Shared Observability Strategy

Use this document to capture telemetry standards that apply to every service in the monorepo.

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

**Frontend Observability:**
* **Web (React):**
  * Uses `@opentelemetry/sdk-trace-web` to generate root spans for user interactions.
  * Propagates `traceparent` headers to backend API calls for end-to-end correlation.
  * Sends telemetry to a relative endpoint (`/otel/v1/traces`) proxied by the serving Nginx container.
  * **Security:** Telemetry ingestion is restricted to authenticated users via the Nginx proxy (see ADR-0001).

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

### 5.4 Security Metrics
* **auth_failures_total** (counter, dimensions: reason): Authentication failures (token invalid, expired, missing scopes)

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

## 7. Alerting & Dashboards
- Azure Monitor / Grafana dashboards for service health, scaling, auth failures.
- Aspire Dashboard for local dev/quick inspection.

## 8. Specification by Example
Capture multi-service observability scenarios (e.g., tracing a chat request across agent → toy → trip → story).
