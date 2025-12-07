# Add-On Service Runbooks

## On-Call Quick Reference
- Dashboards: Add-on overview, Fulfillment, Queue backlog
- Logs: Filter `service=addon` and `order_id`
- Traces: Spans `addon.order`, `addon.fulfill`

## Common Incidents

### Order failures
**Symptoms:** Alert `AddonFailures`; API returns 500 on order create.
**Diagnosis:** Inspect logs for validation errors or downstream Trip/Toy auth issues; check Cosmos throttling.
**Mitigation:**
- Increase RU temporarily; ensure ownership lookup is reachable.
- If Demo Media unavailable, accept order but mark `failed` with user-friendly message; communicate status.

### Fulfillment backlog
**Symptoms:** Alert `QueueBacklog`; `addon_queue_depth` high.
**Diagnosis:** Check KEDA scaling; inspect worker logs for repeated retries.
**Mitigation:**
- Temporarily raise worker replica cap; clear poison messages to dead-letter queue.
- If dependency slow, lower enqueue rate by applying rate limit on order API.

### Slow fulfillment
**Symptoms:** Alert `FulfillmentSlow`; P95 duration high.
**Diagnosis:** Check Demo Media latency, Storage upload times, Trip Service gallery response.
**Mitigation:**
- Parallelize media generation if safe; increase RU on Cosmos; optimize image size before upload.

## Maintenance Tasks
- Rotate Managed Identity access review quarterly.
- Validate idempotency behavior with periodic chaos tests (duplicate messages).
- Rehearse queue DLQ drain and replay procedure.