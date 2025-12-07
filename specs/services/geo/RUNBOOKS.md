# Geo Service Runbooks

## On-Call Quick Reference
- Dashboards: Geo overview, Live map, Queue backlog
- Logs: Filter `service=geo` and `trip_id`
- Traces: Spans `geo.ingest`, `geo.streamTick`

## Common Incidents

### Feed drop from simulator
**Symptoms:** Alert `GeoFeedDrop`; ingest rate near zero.
**Diagnosis:** Check Service Bus topic/subscription metrics; verify simulator is running and authorized; inspect worker logs for auth errors.
**Mitigation:**
- Restart simulator; validate credentials.
- If Service Bus outage, buffer ingestion via temporary in-memory queue; communicate data gap.

### High broadcast latency
**Symptoms:** Alert `GeoLatency`; P95 broadcast latency above target.
**Diagnosis:** Inspect traces for slow Cosmos upserts or saturated pods; check HPA/KEDA status; examine network throttling.
**Mitigation:**
- Scale replicas; increase Cosmos RU for `locations` container temporarily.
- Reduce update frequency from simulator if overwhelming.

### WebSocket churn / disconnect storms
**Symptoms:** Alert `GeoChurn`; users report live map disconnects.
**Diagnosis:** Review logs for disconnect reasons; check gateway timeouts; inspect client versions pushing too many connections.
**Mitigation:**
- Increase WebSocket idle timeout; throttle per-IP connections.
- Roll back to prior image if regressions observed after deploy.

## Maintenance Tasks
- Rotate Azure Maps credentials if key-based; prefer Managed Identity when available.
- Review TTL and partitioning monthly to ensure balanced RU usage.
- Load-test WebSocket fan-out before major demo events.