# Geo Service Architecture Snapshot

Provide a focused view of how this service fits into the broader system while inheriting global context from `../../platform/ARCHITECTURE.md`.

## Context
- Purpose: Ingest and serve live toy location updates; broadcast via WebSocket to map viewers.
- Upstream dependencies: Demo Location simulator (publisher), Trip Service (ownership checks), Toy Service (owner verification), Azure Maps (tiles/geocoding).
- Downstream consumers: Web SPA live map, Agent Service (answers "Where is my toy?"), Story Service (daily recap context).

## Component Diagram
- API surface: REST ingestion endpoint for location updates; WebSocket endpoint for live streaming; optional REST for recent history.
- Data: Cosmos DB container `locations` (HPK `ownerId`, `tripId`, plus time bucket for fan-out control); short TTL to avoid unbounded growth.
- Messaging: Service Bus topic `geo-locations` for simulator ingestion; KEDA worker persists to Cosmos and broadcasts to WebSocket hub.
- External: Azure Maps for reverse geocoding/tiles (no PII sent).

## Data Flow
1. Simulator publishes `{ownerId, tripId, coords, timestamp}` to `geo-locations` topic.
2. KEDA worker consumes, validates ownership, upserts latest location in Cosmos, and pushes to in-memory hub.
3. Web clients connect via WebSocket `/ws/trips/{tripId}`; receive broadcast frames with location payload and trace context.
4. Agent/Story services query last-known location via REST for context.

## Cross-Cutting Concerns
- Resilience: Retry Cosmos on 429; buffer and drop oldest frames if WebSocket backpressure occurs; circuit breaker around Azure Maps calls.
- Performance: Aim P95 ingest-to-broadcast < 1s; throttle per-trip update rate to avoid hot partitions; use HPK to spread writes.
- Compliance: No public map tokens; do not store precise location longer than retention window; follow platform security baseline.

## Decision References
- Uses same gateway exposure and HPA pattern as toy/trip; any deviations captured in service ADRs under `decisions/`.