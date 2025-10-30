# Requirements – Stuffed Toy World Tour

## 1. Overview
The Stuffed Toy World Tour application lets a Toy Owner create whimsical international trips for a plush toy, track live location, view gallery images per leg, order accessories or experiences (add‑ons), and receive daily AI‑generated story recaps – all while demonstrating enterprise microservice patterns (AKS, Cosmos DB, Service Bus, OpenTelemetry, KEDA, Karpenter, APIM, MCP agent).

## 2. Scope (MVP)
Included:
* Toy registration (name, avatar, personality tags)
* Trip creation with ordered legs (locations + optional planned times)
* Gallery images associated to trip legs (uploaded or generated demo images)
* Add‑ons: accessories (hat, outfit, souvenir prop) and experiences (dinner, beer festival, boat ride, coffee & pancake stop)
* Live tracking page (WebSocket) – 1s location updates, ~30s live image frames
* Daily story generation (batch triggered)
* Chat agent (MCP tools) – current status query, place add‑on order, refresh daily story
Excluded (initial MVP): billing/payments, social interaction between different owners, advanced recommendations, consolidated notifications service, complex analytics.

## 3. Persona
Single persona: Toy Owner (audience role). Demo simulators (location, media generation) act behind the scenes and are not exposed as user-facing features.

## 4. Glossary
* Trip: A set of ordered legs for one toy.
* Leg: A single segment/location within a trip.
* Add‑On: Accessory (visual item) OR experience (ephemeral activity) enhancing a leg.
* Gallery Image: Media asset tied to a leg (uploaded or generated).
* Story Version: Daily narrative summary for a trip.
* Live Session: Active WebSocket stream of locations + periodic live images.
* Public Sharing Toggle: Flag enabling location visibility beyond owner (demo only).
* MCP Tool: Agent-accessible operation (e.g., get_trip_status).

## 5. Functional Requirements (User Stories)
1. Register Toy: Owner can register a toy (name, avatar image, personality tags) for personalization.
2. Create Trip: Owner can create a trip with ordered legs.
3. View Live Map: Owner opens live map to see location updates every second.
4. Live Image Stream: Owner sees live image frame refreshed ~every 30s during session.
5. Trip Gallery: Owner views gallery images grouped by leg.
6. Order Add‑On: Owner orders accessory or experience for a specific upcoming leg.
7. Add‑On Fulfillment: Fulfillment image auto‑appears in correct leg gallery.
8. Daily Story Recap: Owner reads a generated daily story summary.
9. Toggle Public Location Sharing: Owner enables/disables public location visibility.
10. Chat Current Status: Owner asks “Where is my toy now?” and receives current location + last image + next leg schedule.
11. Chat Order Add‑On: Owner requests add‑on via chat; system places order and confirms.
12. Manual Story Refresh: Owner requests a refreshed daily story via chat/tool.
13. Start Live Session: Owner starts live tracking; WebSocket connection health confirmed.
14. End Live Session: Owner ends live tracking; stream stops.

## 6. Non‑Functional Requirements
TBD