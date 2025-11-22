# Service Observability Plan – web

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Logs
- **Browser Console**:
  - MSAL logs (Info/Error/Warning) based on `authConfig.ts` settings.
  - API errors logged to console.
- **Server Logs**:
  - Nginx access/error logs (stdout/stderr) captured by container runtime.

## Metrics
- **Client-side**:
  - **Core Web Vitals**: LCP, FID, CLS (planned).
  - **User Actions**: Click events, navigation timing.
- **Server-side**: Nginx request rate, 4xx/5xx rates.

## Tracing
- **Distributed Tracing**:
  - **Library**: `@opentelemetry/sdk-trace-web`, `@opentelemetry/instrumentation-fetch`, `@opentelemetry/instrumentation-document-load`.
  - **Correlation**: Generates root spans for user interactions (e.g., "View Gallery") and injects `traceparent` headers into API calls.
  - **Transport**: Sends OTLP traces to `/otel/v1/traces` (proxied by Nginx to internal collector).
  - **Sampling**: 100% in Dev/Staging, 10% in Production (configurable).

## Alerts
- **Availability**: Synthetic probe against `/` endpoint.
