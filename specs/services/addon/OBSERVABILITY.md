# Service Observability Plan – addon

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
| Metric | Purpose | Target | Dashboard |
| --- | --- | --- | --- |
| `addons_ordered_total` (counter, labels: addon_type, status) | Track demand and error rate | Failure rate < 2% | Add-on overview |
| `addon_fulfillment_duration_seconds` (histogram) | Measure end-to-end fulfillment | P95 < 60s | Fulfillment |
| `addon_queue_depth` (gauge) | Monitor `addon-fulfill` backlog | < 100 for 10m | Fulfillment |
| `addon_worker_retries_total` (counter) | Identify flaky dependencies | Within expected baseline | Fulfillment |

## Logs
- Structured fields: `owner_id`, `trip_id`, `order_id`, `addon_type`, `idempotency_key`, `status`.
- Do not log image content or Storage URLs; log media reference IDs only.

## Traces
- Span `addon.order` (validate -> persist -> enqueue) with attributes `addon_type`, `status`.
- Span `addon.fulfill` (dequeue -> media -> storage -> trip gallery) with downstream span links; propagate trace context to Trip Service when updating gallery.

## Alerts
| Alert | Condition | Severity | Channel | Runbook |
| --- | --- | --- | --- | --- |
| AddonFailures | `addons_ordered_total{status="error"}` ratio > 3% for 5m | High | Ops | Runbook: order failures
| FulfillmentSlow | `addon_fulfillment_duration_seconds` P95 > 90s for 10m | Medium | Ops | Runbook: fulfillment slow
| QueueBacklog | `addon_queue_depth` > 500 for 10m | High | Ops | Runbook: backlog

## Specification by Example
- When Demo Media is down, `addon_worker_retries_total` climbs and AddonFailures fires; worker retries with backoff, marks order failed after max attempts, and leaves trace evidence for investigation.
