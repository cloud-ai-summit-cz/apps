# Service Observability Plan – agent

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
| Metric | Purpose | Target | Dashboard |
| --- | --- | --- | --- |
| `chat_requests_total` (counter, labels: status, streaming) | Traffic + error tracking | Failure rate < 3% | Agent overview |
| `chat_first_token_seconds` (histogram) | Time to first token | P95 < 3s | Agent latency |
| `tool_invocations_total` (counter, labels: tool, status) | Tool health | Failure rate < 5% | Tooling |
| `openai_tokens_total` (counter, labels: direction) | Cost/usage tracking | Within quota | Agent costs |

## Logs
- Structured fields: `session_id`, `owner_id`, `trip_id`, `tool`, `request_id`.
- Redaction: remove PII and prompt content; log prompt/version identifiers only.

## Traces
- Root span `agent.chat` covering request lifecycle; child spans for each tool call and OpenAI invocation.
- Propagate trace context to downstream services to correlate across toy/trip/story/addon/geo.

## Alerts
| Alert | Condition | Severity | Channel | Runbook |
| --- | --- | --- | --- | --- |
| AgentErrors | `chat_requests_total{status="error"}` ratio > 5% for 5m | High | Ops | Runbook: dependency/OpenAI
| SlowFirstToken | `chat_first_token_seconds` P95 > 5s for 10m | Medium | Ops | Runbook: performance
| ToolFailures | `tool_invocations_total{status="error"}` ratio > 8% for 10m | Medium | Ops | Runbook: tool failures

## Specification by Example
- When OpenAI latency spikes, `chat_first_token_seconds` rises and SlowFirstToken fires; traces show long OpenAI span; fallback to cached responses if configured.
