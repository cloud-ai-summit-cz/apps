# Story Service Data Models

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| Story | Cosmos document | Story Service | `stories` container (HPK `ownerId`, `tripId`) | 1.0.0 |

## Detailed Schemas

### Story
- Purpose: Persist generated story recaps per trip/day for retrieval by Web and Agent.
- Storage: Cosmos DB container `stories`; hierarchical partition key `ownerId` → `tripId` to keep owner isolation and high cardinality, preventing hot partitions.
- Lifecycle: Created on generation trigger; updated only for status transitions; TTL optional (e.g., 90 days) to prune stale stories.
- Sample payload:
```json
{
  "id": "story_2025-12-07",
  "ownerId": "<entra_oid>",
  "tripId": "trip_123",
  "storyDate": "2025-12-07",
  "status": "completed",
  "summary": "Fluffy explored Prague’s Old Town...",
  "sections": [
    {"title": "Morning", "content": "Visited Charles Bridge"},
    {"title": "Evening", "content": "Tried trdelník"}
  ],
  "contextVersion": "v1",
  "promptVersion": "v1",
  "model": "gpt-4o-mini",
  "createdAt": "2025-12-07T21:00:00Z",
  "updatedAt": "2025-12-07T21:00:05Z"
}
```
- Validation and limits: Max item size 2 MB; sections truncated server-side; enforce required fields (`ownerId`, `tripId`, `storyDate`, `status`, `summary`).
- Relationships: References trips/toys by ID only (no embedding beyond lightweight context) to avoid oversized documents per Cosmos guidance.