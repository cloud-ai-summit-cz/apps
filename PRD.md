# Product Requirements Document (PRD)

## 1. Metadata
- **Product / Feature Name**: Stuffed Toy World Tour
- **Author(s)**: GitHub Copilot
- **Date**: 2025-11-21
- **Revision**: 1.1.0
- **Status**: Active
- **Related Docs**: specs/platform/ARCHITECTURE.md

## 2. Summary
The Stuffed Toy World Tour application lets a Toy Owner create whimsical international trips for a plush toy, track live location, view gallery images from destinations, order accessories or experiences (add‑ons), and receive daily AI‑generated story recaps – all while demonstrating enterprise microservice patterns (AKS, Cosmos DB, Service Bus, OpenTelemetry, KEDA, Karpenter, APIM, MCP agent).

## 3. Goals & Non-Goals
| Goals | Non-Goals |
| --- | --- |
| **Toy Registration**: Personalize toys with names, avatars, and tags. | **Billing/Payments**: No real money transactions. |
| **Trip Management**: Create and track trips to international destinations. | **Social Interaction**: No following or messaging between owners. |
| **Live Experience**: Real-time location updates and live image streams. | **Advanced Recommendations**: No ML-based trip suggestions. |
| **Add-ons**: Order accessories and experiences to enhance the trip. | **Consolidated Notifications**: No centralized notification center. |
| **AI Integration**: Daily story generation and Chat Agent (MCP) interaction. | **Complex Analytics**: No deep user behavior tracking. |
| **Enterprise Patterns**: Demonstrate AKS, Cosmos DB, Service Bus, etc. | **Production SRE Depth**: Simplified runbooks for demo purposes. |

## 4. Success Metrics
- **Performance**: Token validation latency (cached JWKS) P95 < 5ms.
- **Reliability**: JWKS cache resilient to transient fetch failures.
- **Accuracy**: Clock skew tolerance ±2 minutes for token time claims.
- **Observability**: Auth failures and validation duration metrics emitted.

## 5. Users & Personas
- **Toy Owner (Primary)**: The end-user who registers toys, plans trips, tracks progress, and interacts with the chat agent.
- **Demo Simulators (Internal)**: Background actors that generate location updates and media assets (not user-facing).

## 6. Assumptions & Constraints
- **Security**: Zero static secrets (Managed Identity only). Explicit 401 vs 403 mapping.
- **Privacy**: Global read access model for MVP (revisit for privacy later).
- **Compliance**: SystemPrincipal limited to internal operations; UserPrincipal cannot invoke fulfillment/batch endpoints.
- **Infrastructure**: Azure-centric (AKS, Cosmos DB, Service Bus, Entra ID).

## 7. Specification by Example
| Scenario | Given | When | Then | Automated Test? |
| --- | --- | --- | --- | --- |
| **Register Toy** | A logged-in user | Submits a new toy with name "Fluffy" and an avatar | The toy is created, assigned to the user, and visible in the catalog | Yes (Integration) |
| **Order Add-on** | A toy on an active trip | User orders a "Beret" accessory | The order is accepted, and a fulfillment image appears in the gallery | Yes (E2E) |
| **Live Tracking** | A trip in progress | User opens the live map | Real-time location updates appear every second | Manual (WebSocket) |

## 8. Requirements

### Functional (User Stories)
1.  **Register Toy**: Owner can register a toy (name, avatar image, personality tags).
2.  **Create Trip**: Owner can create a trip to a single destination.
3.  **View Live Map**: Owner opens live map to see location updates every second.
4.  **Live Image Stream**: Owner sees live image frame refreshed ~every 30s.
5.  **Trip Gallery**: Owner views gallery images from the destination.
6.  **Order Add‑On**: Owner orders accessory or experience for the trip.
7.  **Add‑On Fulfillment**: Fulfillment image auto‑appears in trip gallery.
8.  **Daily Story Recap**: Owner reads a generated daily story summary.
9.  **Toggle Public Location Sharing**: Owner enables/disables public location visibility.
10. **Chat Current Status**: Owner asks "Where is my toy now?" and receives status.
11. **Chat Order Add‑On**: Owner requests add‑on via chat; system places order.
12. **Manual Story Refresh**: Owner requests a refreshed daily story via chat/tool.
13. **Start Live Session**: Owner starts live tracking; WebSocket health confirmed.
14. **End Live Session**: Owner ends live tracking; stream stops.
15. **Authenticate User**: Owner must sign in (Entra ID) for access.
16. **Authorized Ordering**: Owner can only order add-ons for their own toys.
17. **Authorized Live Tracking**: Owner can only track their own toys.

### Non-Functional
- **Security**: Token validation < 5ms, Zero static secrets, Explicit 401/403.
- **Reliability**: JWKS cache resilience, Graceful degradation on role failure.
- **Compliance**: Least privilege for SystemPrincipal vs UserPrincipal.

## 9. UX & Flows
- **Web Frontend**:
    - **Landing**: Login via Entra ID.
    - **Catalog**: List of owned toys.
    - **Trip Details**: Itinerary, Gallery, and Live Map (WebSocket).
- **Chat Agent**:
    - Natural language queries for status ("Where is Fluffy?").
    - Action execution via MCP tools (Order Add-on, Refresh Story).

## 10. Dependencies
- **Azure Services**: AKS, Cosmos DB, Storage, APIM, Service Bus.
- **Identity**: Microsoft Entra ID.
- **AI**: Azure OpenAI (for story generation and chat).

## 11. Rollout Plan
- **Phase 1**: Core Services (Toy, Trip) + Web UI.
- **Phase 2**: Live Tracking (Geo Service) + Simulators.
- **Phase 3**: AI Features (Story, Chat Agent).
- **Phase 4**: Add-ons and Fulfillment.

## 12. Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| **Auth Failure** | High | Low | Graceful degradation, structured logging. |
| **Incomplete Observability** | Medium | Medium | Track against `specs/platform/OBSERVABILITY.md`. |
| **Cost Overrun** | Low | Low | Use consumption tiers where possible, auto-scaling. |

## 13. Open Questions
- **Privacy**: How to handle public sharing toggle in a multi-tenant environment? (Currently global read for MVP).
- **WebSocket Auth**: Handling token expiry during long-lived sessions (Client reconnect guidance).

## 14. Change Log
| Date | Author | Change |
| --- | --- | --- |
| 2025-11-21 | GitHub Copilot | Migrated requirements from `docs/REQUIREMENTS.md` to PRD structure. |
