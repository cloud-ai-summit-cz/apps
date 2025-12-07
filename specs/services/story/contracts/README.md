# Story Service Contracts

- **REST**
  - `POST /stories/{tripId}/generate`: Trigger generation for `storyDate` (optional overrides) using caller token; idempotent per (`tripId`, `storyDate`).
  - `GET /stories/{tripId}`: List stories for a trip (paginated, owner-scoped).
  - `GET /stories/{tripId}/{storyId}`: Fetch single story document.
- **Messaging**
  - Service Bus queue `story-jobs`: message `{ ownerId, tripId, storyDate, correlationId }`; consumed by worker via KEDA.
  - Optional event to Trip Service to append gallery note `{ tripId, storyId, summary }`.

OpenAPI/AsyncAPI specs to be authored once endpoints stabilize.