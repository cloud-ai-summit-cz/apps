# Story Service Architecture Snapshot

Provide a focused view of how this service fits into the broader system while inheriting global context from `../../platform/ARCHITECTURE.md`.

## Context
- Purpose: Generate daily narrative recaps for trips using toy, trip, gallery, and location context.
- Upstream dependencies: Trip Service (trip metadata and gallery), Toy Service (owner validation), Geo Service (latest locations), Azure OpenAI for text generation.
- Downstream consumers: Web SPA (reads stories), Agent Service (chat answers reference stories), Trip Service (optionally posts story summaries into gallery feed).

## Component Diagram
- API surface: REST endpoints for manual story generation and retrieval; Service Bus queue `story-jobs` for scheduled compositions (KEDA-driven worker).
- Data: Cosmos DB container `stories` (HPK `ownerId`, `tripId`), Azure Storage (optional cached prompts/results if size grows), no direct blob public access.
- External: Azure OpenAI completion/chat models.

## Data Flow
1. Trigger (scheduler, Agent, or Trip event) emits a message to `story-jobs` with `tripId`, `ownerId`, and `storyDate`.
2. Worker fetches trip, toy, gallery, and recent geo points; assembles prompt; calls Azure OpenAI.
3. Persists story document in Cosmos (`stories`), keyed by `storyId` under HPK (`ownerId`, `tripId`).
4. Emits optional event to Trip Service to add a “Story recap” gallery item.
5. Web/Agent reads latest story via REST.

## Cross-Cutting Concerns
- Resilience: Retry Azure OpenAI with exponential backoff and circuit breaker; retry Cosmos upserts on 429 using retry-after; idempotent writes using `storyId` per (`tripId`, `storyDate`).
- Performance: Target P95 story generation < 30s end-to-end; cache trip/toy context per trip for reuse within a batch window.
- Compliance: No public data exposure; all content scoped by owner; redact PII from prompts/logs; follow platform security and telemetry baselines.

## Decision References
- Reuse platform observability, security, and deployment patterns; any deviations should be recorded as service ADRs in `decisions/`.