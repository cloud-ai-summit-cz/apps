# Shared Observability Strategy

Use this document to capture telemetry standards that apply to every service in the monorepo.

## Instrumentation Baseline
- OpenTelemetry SDKs for logs, metrics, traces.
- OTEL Collector as central pipeline routing to Azure Monitor, App Insights, Grafana.

## Metrics & SLOs
Define org-wide SLIs/SLOs (request latency, error rates, availability) and which services must emit them. Reuse and refine the metrics already described in the original `docs/OBSERVABILITY.md` (e.g., story_jobs_pending, media_generation_queue_depth, auth_failures_total).

## Tracing
- W3C tracecontext propagation.
- Span naming conventions aligned with operations like toy.register, trip.create, addon.order, story.compose, geo.streamTick.

## Logging
- Structured JSON logs with correlation IDs and principal classification.

## Alerting & Dashboards
- Azure Monitor / Grafana dashboards for service health, scaling, auth failures.

## Specification by Example
Capture multi-service observability scenarios (e.g., tracing a chat request across agent → toy → trip → story).
