# Service Data Models – demo-data-init

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| ImportRequest | Pydantic model | demo-data-init service | Code | 1.0.0 |

## Detailed Schemas

### ImportRequest (Request)
Payload for triggering a data import.

| Field | Type | Description |
| --- | --- | --- |
| `include_toys` | boolean | Whether toy profiles should be reseeded (default: true). |
| `include_trips` | boolean | Whether trip itineraries should be reseeded (default: true). |

### ImportResponse (Response)
Result of the import operation.

| Field | Type | Description |
| --- | --- | --- |
| `include_toys` | boolean | Echo of request parameter. |
| `include_trips` | boolean | Echo of request parameter. |
| `summary` | OperationSummary | Statistics about the operation. |
| `duration_ms` | integer | Total runtime in milliseconds. |

### OperationSummary (Sub-resource)
Processing statistics.

| Field | Type | Description |
| --- | --- | --- |
| `toys_processed` | integer | Count of toys processed. |
| `toy_failures` | integer | Count of toy failures. |
| `toy_avatars_uploaded` | integer | Count of avatars uploaded. |
| `trips_processed` | integer | Count of trips processed. |
| `trip_failures` | integer | Count of trip failures. |
| `images_uploaded` | integer | Count of gallery images uploaded. |
