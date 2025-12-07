# Add-On Service Data Models

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| AddonOrder | Cosmos document | Add-On Service | `addons` container (HPK `ownerId`, `tripId`) | 1.0.0 |

## Detailed Schemas

### AddonOrder
- Purpose: Track lifecycle of an add-on order from request through fulfillment.
- Storage: Cosmos DB container `addons`; hierarchical partition key `ownerId` → `tripId` for high cardinality and owner isolation.
- Lifecycle: `pending` -> `in_progress` -> `fulfilled` or `failed`; fulfillment worker updates status and media reference.
- Sample payload:
```json
{
  "id": "addon_123",
  "ownerId": "<entra_oid>",
  "tripId": "trip_123",
  "addonType": "beret",
  "notes": "Make it red",
  "status": "fulfilled",
  "mediaRef": {"type": "gallery", "blobName": "gallery/trip_123/beret.png"},
  "idempotencyKey": "req-abc",
  "requestedAt": "2025-12-07T21:00:00Z",
  "fulfilledAt": "2025-12-07T21:00:45Z",
  "errorMessage": null
}
```
- Validation: Require `ownerId`, `tripId`, `addonType`; length limits on `notes`; enforce 2 MB document cap.
- Relationships: References Trip by ID; fulfillment media stored externally (no binary in document) to respect Cosmos size limits.