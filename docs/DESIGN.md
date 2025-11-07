# Design – Stuffed Toy World Tour

## 1. Architecture Goals
Demonstrate modern cloud-native microservices on AKS with: clear service boundaries, event-driven async flows, OpenTelemetry instrumentation, autoscaling via KEDA, dynamic node provisioning via Karpenter, API governance with APIM, and agent integration through MCP.

## 2. Microservice Inventory
| Service | Shortname | Purpose |
|---------|-----------|---------|
| Toy Registry & Profiles | toy | Manage toy profiles (name, avatar, personality tags) for personalization. |
| Trip & Gallery Service | trip | Create trips to single destinations, store gallery images from destinations, expose trip detail & gallery listing. |
| Add‑On Services (Accessories & Experiences) | addon | Handle ordering & fulfillment of accessories (hat, outfit, souvenir prop) OR experiences (dinner, beer festival, boat rental, coffee & pancake stop); publish fulfillment image(s) to trip gallery. |
| Geo Location & Live Stream | geo | Accept periodic location pings, manage public share flag, stream location (1s intervals) & live image frames (30s) via WebSocket; expose map feed. |
| Story Composer (Batch AI) | story | Generate daily narrative/story recap using destinations, gallery, add-ons, personality tags; store versions. |
| AI Agent Service (Chat Backend via MCP) | agent | Backend for in‑app chat; uses MCP protocol tools to call other services (toy, trip, addon, story, geo) and compose responses (status, recent media, addon request, story refresh). |
| Location Tracking Simulator (Demo) | demo-location | Emit synthetic location pings & occasional live frames for active trips (feeds geo service). |
| Image Generation Service (Demo) | demo-media | Listen to trip/addon events; generate synthetic images (toy in location / addon fulfillment) and post to trip gallery. |

Deferred / Optional: Recommendations, Billing/Credits, Consolidated Notifications, Route Optimization ephemeral planner.

### Add-On Categories
Accessories: hat, outfit, souvenir prop. Experiences: dinner, beer at festival, boat rental, coffee & pancake stop.

## 3. Runtime Interaction Overview
* REST (FastAPI) via APIM: toy registration, trip creation, add‑on ordering, gallery listing, story retrieval.
* WebSocket: geo service streaming location + periodic live image frames.
* Batch / Asynchronous: story service processes recap jobs triggered by message burst or schedule.
* MCP (Agent): The chat backend (agent service) invokes MCP protocol tools that represent other services' capabilities; it does not expose those tools itself—rather it orchestrates calls and returns aggregated chat responses.

## 4. Inter-Service Communication
* Synchronous REST between frontend (through APIM) and core services.
* Service Bus topics/queues (planned) for: story.daily.requested, addon.fulfillment.requested, media.generation.requested, fulfillment.completed.
* Event usage currently abstracted; schema definitions pending.

## 5. Data Storage Strategy

### 5.1 Cosmos DB
Logical containers (indicative):
* toys – partition by toy_id
* trips – partition by trip_id (embed destination & gallery metadata)
* addons – partition by addon_order_id
* stories – partition by trip_id/date composite or trip_id
* locations – partition by trip_id or date bucket (time-series)
Partition Rationale: locality for trip operations; independent scaling for location ingestion; distinct containers for operational vs historical narrative.

### 5.2 Blob Storage (Images)
**Access Pattern:** Private endpoints with Entra authentication required (enterprise policy).
* **Avatar images:** Stored in `avatars` container, accessed via toy service proxy using managed identity
* **Gallery images:** Stored in `gallery` container, accessed via trip service proxy using managed identity
* **Add-on fulfillment images:** Stored in `addons` container, accessed via addon service proxy using managed identity

**No SAS tokens or public blob URLs permitted.** Services store internal blob references (container + blob name) in database fields and serve images through authenticated proxy endpoints. Frontend requests images from service endpoints (e.g., `GET /toy/{id}/avatar`), which stream content from blob storage using managed identity.

**Performance considerations:**
* Services implement streaming responses to avoid memory bloat
* Cache-Control headers enable browser/CDN caching
* Future: Azure CDN Premium with Private Link origin if needed

## 6. Observability & Telemetry
Instrumentation:
* OTEL spans: toy.register, trip.create, trip.gallery.upload, addon.order, addon.fulfill, story.compose, gallery.addImage, geo.streamTick.
* Context propagation via correlation_id and trace headers through message envelopes.
Metrics (Prometheus): story_jobs_pending, story_context_bytes, addon_requests_total, location_updates_per_second, media_generation_queue_depth, chat_status_latency_seconds.
Dashboards (Grafana): scaling events timeline, story memory usage, media queue depth vs replicas, WebSocket connection count, error rates.

## 7. Scaling & Autoscaling
KEDA:
* Triggers: story_jobs_pending (batch story), media_generation_queue_depth (demo media), optional location_ingest_rps (future).
Karpenter:
* Provision memory-optimized nodes for story service when average container memory > threshold.
* Provision CPU/GPU optimized nodes for demo-media during image burst.
* Node labels/taints isolate demo workloads from core services.

## 8. Security & Identity
* Managed identity per service for Cosmos DB, Service Bus, Key Vault secret access, **and Blob Storage access**.
* **Blob Storage:** Private endpoints with Entra authentication enforced; no SAS tokens or anonymous access permitted (enterprise policy).
* APIM enforces rate limits (trip creation, addon order, chat tools, **image uploads**).
* Public sharing disabled by default; explicit toggle sets location visibility scope.
* Secrets: AI image generation credentials in Key Vault; environment references via managed identity.

### 8.1 Identity Sources
| Principal Type | Origin | Token Characteristics | Typical Usage |
|----------------|--------|-----------------------|---------------|
| UserPrincipal | Entra ID interactive (MSAL PKCE) | JWT contains `oid`, `scp` or `roles`, audience = Application ID URI | All synchronous frontend → service REST calls |
| SystemPrincipal | Workload/Managed Identity (AKS federated service account) | JWT contains `appid` / `azp` (no `oid`), `roles` includes `System.Service` | Background fulfillment, batch story composition, internal service → service calls |

All principals share a common validation pipeline; difference is classification based on claim presence.

### 8.2 Token Validation Flow
1. Extract `Authorization: Bearer <token>` header.
2. Decode header, select JWKS key by `kid` (cached; refresh on miss or daily).
3. Validate signature, issuer (tenant v2 endpoint), audience (configured Application ID URI), time (`exp`, `nbf` with ±2m clock skew allowance).
4. Extract scopes (`scp`) or roles (`roles`). Require either `App.Access` scope OR one of declared roles (`Toy.ReadWrite`, `System.Service`).
5. Classify principal: presence of `oid` → UserPrincipal; else presence of `appid`/`azp` with `System.Service` role → SystemPrincipal.
6. Attach principal + token metadata to request context for downstream permission checks & tracing.

Failure mapping: missing/invalid token → 401; valid token but insufficient permission for the resource → 403.

### 8.3 Permission Matrix (Summary)
| Action | UserPrincipal | SystemPrincipal |
|--------|---------------|----------------|
| Read any toy/trip/gallery/story | Allowed | Allowed |
| Create trip / order add-on | Allowed only if user owns toy | Allowed |
| Live geo tracking (start/subscribe) | Only owner of toy | Allowed |
| Story compose trigger | Not directly (future) | Allowed |
| Fulfillment posting (media/add-on) | Not allowed | Allowed |

Ownership check uses stored `owner_oid` on `toy` entity vs principal `oid`.

### 8.4 Non-Functional Security Goals
| Goal | Target |
|------|--------|
| Token validation latency (cached JWKS) | <5ms P95 |
| JWKS cache refresh | 24h or key miss |
| Zero secrets for Azure SDK access | Enforced (Managed Identity only) |
| Auth failure metric surfacing | `auth_failures_total{reason}` |

### 8.5 Observability Hooks (Auth)
Add spans around token validation with attributes: `principal.type`, `principal.oid` (optional/anonymized). Metrics: `auth_token_validation_duration_ms` histogram.

### 8.6 WebSocket Considerations
Token validated at connection upgrade; session length must not exceed token expiry. Recommend client-side proactive refresh + reconnect when token <5m to expiry.

### 8.7 Future Extensibility
* Introduce granular roles (e.g., `Toy.ReadAll`, `Trip.WriteOwn`) if global read model changes.
* On-Behalf-Of flow for background service acting under user context (not required MVP).
* Potential privacy enhancement: restrict read-all; add access lists per toy.

## 9. MCP Agent Integration
The agent service acts as a chat backend that consumes MCP tools exposed by other domain services (or an MCP adapter/gateway). Tools conceptually available to the agent (implemented by respective services or adapters):
* get_trip_status(trip_id)
* list_recent_media(trip_id, limit)
* request_addon(trip_id, addon_type)
* refresh_daily_story(trip_id)
* start_live_session(trip_id)
* end_live_session(trip_id)

Flow:
1. Chat UI sends natural language query to agent backend.
2. Agent parses intent → selects appropriate MCP tool calls.
3. Agent invokes tools (MCP protocol) against service endpoints/APIM.
4. Aggregates responses (e.g., trip status + last media + destination info) and returns structured chat message.

Low Latency Goal: <1s P95 for multi-tool status queries with parallel downstream requests.

## 10. Deployment Topology
* AKS cluster namespaces: core (toy, trip, addon, geo, story, agent), demo (demo-location, demo-media), observability (otel-collector).
* APIM gateway fronting public endpoints.
* Azure Maps for map rendering; key stored in Key Vault.
* Service Bus namespace for asynchronous workloads.
* App Insights for traces/logs; Grafana for metrics dashboards.

## 11. Failure Handling & Resilience
* Image generation failures: gallery entry with error state + placeholder image.
* Story composition retry (max 2) on transient errors.
* WebSocket heartbeat; client reconnect if > N missed heartbeats.
* Rate-limits / circuit breakers at APIM for potential misuse.

## 12. Extensibility & Deferred Components
Future additions: recommendation engine (popular routes, suggested experiences), billing/credits, consolidated notifications service, route optimization ephemeral planner, moderation pipeline if public features broaden.

## 13. Configuration & Environment
* Config via ConfigMaps/Secrets (non-sensitive vs sensitive). Key Vault integration for sensitive keys.
* Feature flags: enable_live_stream, enable_batch_story_demo.
* Resource requests sized for baseline; autoscaling handles surges.

## 14. Pending Definitions / Open Questions
* Event envelope schema & versioning strategy.
* Max concurrent story jobs before backpressure.
* Strategy for large trip archives (cold storage vs active container).
* Add-on experience textual note normalization for story composer.

## 15. Risks & Mitigations (Design View)
| Risk | Design Concern | Mitigation |
|------|----------------|-----------|
| Memory spikes from large story batches | Node pressure | Memory thresholds + Karpenter provisioning |
| High location ping throughput | WebSocket saturation | Option to buffer and downsample broadcast |
| Chat tool fan-out latency | Aggregate response delay | Parallel downstream calls + caching of static trip metadata |
| Image burst GPU contention | Slow generation | Separate node pool with taints, queue-based smoothing |

## 16. Sequence & Flow (Placeholder)
Will add diagrams (live map stream, batch story generation pipeline) after endpoint & event schema confirmation.

---
Approved design baseline; architectural changes will be proposed before modification.
