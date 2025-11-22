# Architecture Decision Record (ADR)

- **ADR ID**: 0001
- **Title**: Frontend Observability via Secure Reverse Proxy
- **Status**: Accepted
- **Date**: 2025-11-22
- **Authors**: GitHub Copilot
- **Related Docs**: `specs/platform/OBSERVABILITY.md`, `specs/services/web/OBSERVABILITY.md`

## 1. Context
- **Business Problem**: Currently, frontend user actions (e.g., "Load Gallery") trigger multiple backend API calls that appear as disconnected traces. We lack correlation between the user intent and the resulting backend operations.
- **Technical Driver**: We need to enable OpenTelemetry (OTEL) tracing in the React frontend to generate a root span and propagate trace context to backend services.
- **Constraints**:
  - The OTEL Collector is internal to the cluster and should not be exposed publicly without security.
  - We cannot store secrets (API keys) securely in the React client code.
  - We must prevent unauthenticated users from flooding our telemetry system.

## 2. Decision Statement
We will implement frontend tracing by configuring the Nginx container (which serves the React app) to act as a reverse proxy for OTEL telemetry. The React app will send traces to a relative endpoint on the same domain, and Nginx will forward these to the internal OTEL collector, enforcing authentication via session cookies.

## 3. Specification by Example Snapshot
- **Scenario**: Authenticated user views a trip gallery.
  - **Given** a user is logged in and has a valid session cookie.
  - **When** the user navigates to the gallery page.
  - **Then** the React app generates a root span "view_gallery".
  - **And** sends telemetry to `https://<web-host>/otel/v1/traces`.
  - **And** Nginx validates the session and forwards the payload to `http://otel-collector.observability.svc.cluster.local:4318/v1/traces`.
  - **And** backend API calls include the `traceparent` header linking them to the "view_gallery" span.

- **Scenario**: Unauthenticated user attempts to send traces.
  - **Given** a user without a valid session.
  - **When** they send a POST request to `/otel/v1/traces`.
  - **Then** Nginx returns `401 Unauthorized` or `403 Forbidden` and drops the request.

## 4. Options Considered
| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| **Direct to Public Collector** | Expose OTEL Collector via Ingress/Gateway with API Key. | Simple architecture. | Requires managing public keys; keys in frontend are insecure; CORS issues. |
| **BFF / API Gateway** | Route telemetry through the main API Gateway. | Centralized auth. | Adds load to business gateway; complex routing configuration. |
| **Nginx Sidecar Proxy** | Use the existing serving container (Nginx) to proxy. | No CORS; reuses existing auth session; no new infrastructure; secure by design. | Requires Nginx config update; couples serving with telemetry proxying. |

## 5. Decision Drivers
- **Security**: Must not expose internal collector or require secrets in the browser.
- **Correlation**: Need to link frontend actions with backend traces.
- **Simplicity**: Leverage existing infrastructure (Nginx container) without adding new public endpoints.

## 6. Consequences
- **Positive Outcomes**:
  - Full end-to-end tracing from user click to database query.
  - Secure telemetry ingestion without public API keys.
  - No CORS configuration needed for telemetry.
- **Trade-offs**:
  - Nginx configuration becomes slightly more complex.
  - Increased CPU/Memory usage on the web container to handle proxy traffic.
- **Operational Impacts**:
  - Need to monitor Nginx proxy performance.
  - Need to ensure the internal collector DNS is resolvable from the web pod.

## 7. Implementation Plan
- **Frontend**: Instrument React app with `@opentelemetry/sdk-trace-web` and `BatchSpanProcessor`.
- **Proxy**: Update `nginx.conf` to forward `/otel/` traffic to the collector service.
- **Security**: Configure Nginx to check for session presence (if applicable) or rate limit.
- **Docs**: Update Observability and Security specs.

## 8. Verification
- **Test**: Log in, perform an action, check Jaeger/Tempo for a trace starting with a browser span and containing backend child spans.
- **Security Test**: Attempt to `curl` the `/otel/` endpoint without cookies and verify rejection.

## 9. Follow-up Actions
- Update `specs/services/web/contracts/otel-proxy.md`.
- Implement Nginx config changes.
- Implement React instrumentation.

## 10. Change Log
| Date | Author | Update |
| --- | --- | --- |
| 2025-11-22 | GitHub Copilot | Initial creation |
