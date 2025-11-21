# Service Observability Plan – demo-data-init

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **Standard HTTP telemetry**: Request count, duration, status codes (via OpenTelemetry SDK)

## Logs
- Log per-import summaries including durations and counts.

## Traces
- Trace import operations.

## Alerts
- Alert on import failures.
