# Agent Service Runbooks

## On-Call Quick Reference
- Dashboards: Agent overview, Agent latency, Tooling errors
- Logs: Filter `service=agent` and `session_id`
- Traces: Root span `agent.chat` with child tool spans

## Common Incidents

### OpenAI outage or throttling
**Symptoms:** Alert `AgentErrors` or `SlowFirstToken`; traces show long/failed OpenAI spans.
**Diagnosis:** Check OpenAI status/quota; review token usage metrics.
**Mitigation:**
- Reduce concurrency; switch to smaller model if allowed.
- Serve cached or partial responses; communicate degraded mode.
- If unavailable, short-circuit chat with friendly fallback.

### Downstream service failure (toy/trip/story/addon/geo)
**Symptoms:** ToolFailures alert; traces show downstream 5xx.
**Diagnosis:** Identify failing tool; verify auth and endpoint health.
**Mitigation:**
- Temporarily disable failing tool and inform users; continue read-only responses using cached state.
- Retry idempotent GETs with backoff.

### Session store issues (Cosmos 429/5xx)
**Symptoms:** Chat persistence errors; elevated 500s.
**Diagnosis:** Check Cosmos RU and latency; inspect HPK distribution.
**Mitigation:**
- Increase RU temporarily; ensure HPK is balanced.
- Enable in-memory fallback cache for ongoing sessions; replay to Cosmos once healthy.

## Maintenance Tasks
- Review and rotate prompt/tool versions quarterly.
- Audit Managed Identity permissions for downstream services.
- Load-test SSE streaming path before major events.