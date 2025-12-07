# Add-On Service Architecture Snapshot

Provide a focused view of how this service fits into the broader system while inheriting global context from `../../platform/ARCHITECTURE.md`.

## Context
- Purpose: Accept add-on orders (accessories/experiences) for trips and orchestrate fulfillment images that appear in galleries.
- Upstream dependencies: Web SPA and Agent Service for order placement; Trip/Toy services for ownership validation.
- Downstream integrations: Demo Media generator (simulated fulfillment), Trip Service gallery endpoint for adding fulfillment images, Azure Storage for generated assets if needed.

## Component Diagram
- API surface: REST endpoints to create/list orders; webhook/internal endpoint for fulfillment updates.
- Data: Cosmos DB container `addons` (HPK `ownerId`, `tripId`).
- Messaging: Service Bus queue `addon-fulfill` for async fulfillment jobs; KEDA worker processes and posts results to Trip gallery.

## Data Flow
1. User places order via `POST /trips/{tripId}/addons` with caller token.
2. Service validates ownership via Trip/Toy; writes order document (`status=pending`) to Cosmos; enqueues message to `addon-fulfill`.
3. Worker consumes queue, calls Demo Media to generate image, uploads to storage, updates order status to `fulfilled`, and calls Trip Service to append gallery item.
4. Web/Agent polls/listens for order status and gallery updates.

## Cross-Cutting Concerns
- Resilience: Idempotent order creation via client-supplied idempotency key; retries for Demo Media/Storage with backoff; handle poison messages for failed fulfillments.
- Performance: Target P95 order acceptance < 500ms; fulfillment end-to-end P95 < 60s.
- Compliance: No public blob URLs; gallery updates only via authenticated service call.

## Decision References
- Mirrors toy/trip security and deployment patterns; fulfillment workflow specifics to be captured in `decisions/` if diverging.