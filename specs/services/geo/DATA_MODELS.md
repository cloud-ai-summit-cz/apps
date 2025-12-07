# Geo Service Data Models

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| LocationSnapshot | Cosmos document | Geo Service | `locations` container (HPK `ownerId`, `tripId`, `bucketDate`) | 1.0.0 |

## Detailed Schemas

### LocationSnapshot
- Purpose: Store latest and recent location points per trip for map rendering and history queries.
- Storage: Cosmos DB container `locations`; hierarchical partition key `ownerId` → `tripId` → `bucketDate` (YYYY-MM-DD) to spread writes and keep targeted queries per trip/day.
- Lifecycle: Upserted on each ingestion; optional TTL (e.g., 7 days) to bound storage; `isLatest` flag for quick fetch.
- Sample payload:
```json
{
  "id": "loc_2025-12-07T21:00:00Z",
  "ownerId": "<entra_oid>",
  "tripId": "trip_123",
  "bucketDate": "2025-12-07",
  "coordinates": {"lat": 50.087, "lon": 14.421},
  "speedKph": 12.3,
  "headingDeg": 180,
  "accuracyMeters": 5,
  "isLatest": true,
  "capturedAt": "2025-12-07T21:00:00Z",
  "ingestedAt": "2025-12-07T21:00:01Z"
}
```
- Validation: Require `ownerId`, `tripId`, `coordinates`, `capturedAt`; clamp precision to avoid oversized payloads; enforce 2 MB limit.
- Relationships: References trip by `tripId`; no embedding of map tiles or images; history queries limited to per-trip partitions to avoid cross-partition scans.