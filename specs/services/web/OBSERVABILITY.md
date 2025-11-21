# Service Observability Plan – web

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Logs
- **Browser Console**:
  - MSAL logs (Info/Error/Warning) based on `authConfig.ts` settings.
  - API errors logged to console.
- **Server Logs**:
  - Nginx access/error logs (stdout/stderr) captured by container runtime.

## Metrics
- **Client-side**: None currently instrumented (e.g., no App Insights or GA).
- **Server-side**: Nginx request rate, 4xx/5xx rates.

## Tracing
- **Distributed Tracing**: Not currently propagating W3C trace context headers to backend services manually (relies on browser/network stack).

## Alerts
- **Availability**: Synthetic probe against `/` endpoint.
