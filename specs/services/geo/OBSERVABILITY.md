# Service Observability Plan – geo

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
| Metric | Purpose | Target | Dashboard |
| --- | --- | --- | --- |
| `location_ingest_rate` (gauge) | Monitor simulator feed health | Within expected band per env | Geo overview |
| `websocket_connections_active` (gauge) | Track connected clients | Capacity headroom > 20% | Live map |
| `broadcast_latency_seconds` (histogram) | Ingest-to-broadcast latency | P95 < 1s | Live map |
| `ws_disconnects_total` (counter, reason label) | Identify churn causes | No sustained spikes | Live map |

## Logs
- Structured fields: `owner_id`, `trip_id`, `captured_at`, `ws_session_id`, `disconnect_reason`.
- Log connect/disconnect events at INFO; drop individual location payload logging to DEBUG to avoid noise.

## Traces
- Span `geo.ingest` (queue consume -> validate -> upsert) and `geo.streamTick` (broadcast) with attributes `trip_id`, `owner_id`, `payload_age_ms`.
- Propagate trace context to WebSocket messages where supported (e.g., correlation id).

## Alerts
| Alert | Condition | Severity | Channel | Runbook |
| --- | --- | --- | --- | --- |
| GeoFeedDrop | `location_ingest_rate` drops below threshold for 5m | High | Ops | Runbook: feed drop
| GeoLatency | `broadcast_latency_seconds` P95 > 2s for 10m | Medium | Ops | Runbook: latency
| GeoChurn | `ws_disconnects_total{reason="abnormal"}` spike 3x baseline | Medium | Ops | Runbook: churn

## Specification by Example
- Given the simulator stops publishing, `location_ingest_rate` falls and GeoFeedDrop fires; on-call checks Service Bus and restarts simulator, verifying metrics recover.
