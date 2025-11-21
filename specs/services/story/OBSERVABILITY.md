# Service Observability Plan – story

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **story_compositions_requested_total** (counter): Story generation requests
- **story_jobs_pending** (gauge): Pending story composition jobs (KEDA trigger)

## Logs
- Ensure `user_id` and `trip_id` are included in structured logs.

## Traces
- **story.compose:** Story generation (context gathering, AI invocation, storage)

## Alerts
- Alert on high `story_jobs_pending` count (backlog).
- Alert on high failure rate for `story.compose`.
