# Service Observability Plan – story

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
| Metric | Purpose | Target | Dashboard |
| --- | --- | --- | --- |
| `story_compositions_requested_total` (counter, labels: status, model) | Volume + success/failure tracking | Failure rate < 2% | Story overview |
| `story_jobs_pending` (gauge) | Queue backlog for KEDA | < 50 pending for 5m | Ops backlog |
| `story_generation_duration_seconds` (histogram) | End-to-end generation latency | P95 < 30s | Story latency |

## Logs
- Structured fields: `owner_id`, `trip_id`, `story_id`, `story_date`, `request_id`, `model`.
- PII handling: do not log raw story text; log prompt versions only.

## Traces
- Span `story.compose` covering context fetch, OpenAI call, and Cosmos write; include attributes for `trip_id`, `model`, `status`.
- Propagate trace context to downstream calls (Trip/Toy/Geo, Azure OpenAI) via W3C Trace Context.

## Alerts
| Alert | Condition | Severity | Channel | Runbook |
| --- | --- | --- | --- | --- |
| StoryBacklog | `story_jobs_pending > 200` for 10m | High | Ops | Runbook: backlog
| StoryFailures | `story_compositions_requested_total{status="error"}` ratio > 5% for 5m | High | Ops | Runbook: openai/cosmos
| SlowStories | `story_generation_duration_seconds` P95 > 45s for 15m | Medium | Ops | Runbook: latency

## Specification by Example
- Given OpenAI returns 429, the service retries with jitter and records `status=retry` before succeeding; traces show retry spans and latency histogram shifts but success ratio remains healthy.
