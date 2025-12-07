# Story Service Runbooks

## On-Call Quick Reference
- Dashboards: Story overview, Story latency, Queue backlog
- Logs: Filter by `service=story` and `story_id`
- Traces: Search span `story.compose`

## Common Incidents

### Backlog of story jobs
**Symptoms:** Alert `StoryBacklog` firing; increasing `story_jobs_pending`.
**Diagnosis:** Check Service Bus queue length and KEDA ScaledObject status; inspect worker pod logs for errors.
**Mitigation:**
- Scale HPA/KEDA max replicas temporarily.
- Purge malformed messages only if payload invalid (coordinate with product owner).
- If downstream dependency failing, pause new enqueues until stable.

### High failure rate from Azure OpenAI
**Symptoms:** Alert `StoryFailures`; spans show `status=error` on OpenAI calls.
**Diagnosis:** Verify OpenAI health, quota, and rate limits; check prompt size vs token limits.
**Mitigation:**
- Reduce concurrency by lowering worker parallelism.
- Retry with backoff; consider fallback to smaller model if allowed.
- If outage, disable queue triggers and communicate ETA.

### Slow story generation
**Symptoms:** Alert `SlowStories` firing; P95 above target.
**Diagnosis:** Inspect traces for long-running context fetch or OpenAI latency; check Cosmos RU throttling (429).
**Mitigation:**
- Increase RU for `stories` container temporarily.
- Cache trip context; trim prompt size.
- Scale replicas to reduce per-pod load.

## Maintenance Tasks
- Rotate Managed Identity permissions review quarterly.
- Tune KEDA scaling thresholds based on observed queue patterns.
- Review prompt versions and archive obsolete ones; remove stories older than TTL via scheduled job.