# Service Observability Plan – geo

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **location_updates_per_second** (gauge): Location ping ingestion rate
- **websocket_connections_active** (gauge): Active WebSocket connections

## Logs
- Log connection/disconnection events.

## Traces
- **geo.streamTick:** Location update broadcast (ingestion, WebSocket fan-out)

## Alerts
- Alert on sudden drop in `location_updates_per_second`.
- Alert on high WebSocket connection churn.
