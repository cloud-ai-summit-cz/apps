# Agent Service Architecture Snapshot

Provide a focused view of how this service fits into the broader system while inheriting global context from `../../platform/ARCHITECTURE.md`.

## Context
- Purpose: Chat backend orchestrating MCP tools to answer user queries and act on their behalf (order add-ons, fetch status, trigger stories).
- Upstream dependencies: Web SPA chat client; auth via Entra.
- Downstream integrations: Toy, Trip, Geo, Story, Addon services; Azure OpenAI for reasoning; Service Bus (optional) for long-running tool calls.

## Component Diagram
- API surface: REST/SSE endpoint for chat turns; admin endpoints for health/metrics.
- Data: Cosmos DB container `chat_sessions` (HPK `ownerId`, `sessionId`) storing short-term context and tool traces; optional ephemeral cache.
- Tools: HTTP clients for toy/trip/story/geo/addon; Azure OpenAI model for orchestration; Service Bus topic `agent-tool-events` for async tool completions if needed.

## Data Flow
1. User sends chat message with session id.
2. Agent fetches session context from Cosmos, calls downstream services for fresh state (toy/trip/story/geo/addon), assembles tool calls.
3. Executes Azure OpenAI call with tool schema; issues downstream mutations (e.g., add-on order) when required.
4. Streams response back (SSE) and persists turn to `chat_sessions`.

## Cross-Cutting Concerns
- Resilience: Timebox tool calls; degrade gracefully when optional data (e.g., gallery) unavailable; retries with backoff for idempotent GETs.
- Performance: Target P95 chat response (first token) < 3s; total < 10s for tool-heavy flows; cache static toy/trip metadata per session.
- Compliance: Strict PII handling; sanitize user input; guard against prompt injection by constraining tools and grounding sources.

## Decision References
- Uses shared gateway, OTEL, and HPA patterns; any orchestration-specific choices documented in service ADRs under `decisions/`.