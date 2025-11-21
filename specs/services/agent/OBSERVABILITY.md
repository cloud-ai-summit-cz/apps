# Service Observability Plan – agent

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **Standard HTTP telemetry**: Request count, duration, status codes.

## Logs
- Log chat session IDs and user interactions (redacted).

## Traces
- Trace chat requests across services (agent -> toy -> trip -> story).

## Alerts
- Alert on high error rates for chat endpoints.
