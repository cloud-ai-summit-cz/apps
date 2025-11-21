# Service Observability Plan – toy

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **toys_viewed_total** (counter, dimensions: user_id, is_admin): Total toy profile views
- **toys_registered_total** (counter, dimensions: is_admin): New toy registrations

## Logs
Document log fields and PII rules for toy requests.
- Ensure `user_id` and `toy_id` are included in structured logs where available.
- Mask PII in logs.

## Traces
Detail spans like toy.register and avatar upload flows.
- **toy.register:** Toy registration flow (validation, storage, avatar upload)

## Alerts
Capture any toy-specific alerts (e.g., persistent 5xx on create or avatar operations).
- Alert on high failure rate for `toy.register` operation.
