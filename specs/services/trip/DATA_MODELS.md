# Service Data Models – trip

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| Trip | Cosmos document / Pydantic model | trip service | Code + platform DATA_MODELS | 1.0.0 |

## Detailed Schemas

### Trip (Resource)
The complete representation of a Trip.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Unique trip identifier. |
| `toy_id` | UUID | ID of the toy taking this trip. |
| `owner_oid` | string | Entra object ID of the toy owner (denormalized). |
| `title` | string | Trip title (1-200 chars). |
| `description` | string? | Trip description (max 1000 chars). |
| `location_name` | string | Destination city or location. |
| `country_code` | string | ISO 3166-1 alpha-2 country code (uppercase). |
| `public_tracking_enabled` | boolean | Enable public location sharing. |
| `status` | enum | `planned`, `in_progress`, `completed`, `cancelled`. |
| `gallery` | list[GalleryImage] | Collection of images associated with the trip. |
| `created_at` | datetime | Creation timestamp (UTC). |
| `updated_at` | datetime | Last modification timestamp (UTC). |

### GalleryImage (Sub-resource)
Image metadata embedded in a Trip.

| Field | Type | Description |
| --- | --- | --- |
| `image_id` | UUID | Unique image identifier. |
| `blob_name` | string | Internal blob storage reference. |
| `landmark` | string? | Landmark name featured in the image. |
| `caption` | string? | Optional image caption. |
| `source` | string | Image source (default: "user"). |
| `uploaded_at` | datetime | Upload timestamp (UTC). |

### TripCreate (Request)
Payload for creating a new trip.

| Field | Type | Description |
| --- | --- | --- |
| `toy_id` | UUID | ID of the toy taking this trip. |
| `title` | string | Trip title. |
| `description` | string? | Trip description. |
| `location_name` | string | Destination city or location. |
| `country_code` | string | ISO country code. |
| `public_tracking_enabled` | boolean | Enable public location sharing (default: false). |
| `id` | UUID? | Optional explicit ID (used for imports). |

### TripUpdate (Request)
Payload for partial updates.

| Field | Type | Description |
| --- | --- | --- |
| `title` | string? | New title. |
| `description` | string? | New description. |
| `location_name` | string? | New location name. |
| `country_code` | string? | New country code. |
| `public_tracking_enabled` | boolean? | Update tracking status. |
| `status` | enum? | Update trip status. |

### TripDocument (Storage)
Cosmos DB representation. Extends `Trip`.

| Field | Type | Description |
| --- | --- | --- |
| `trip_id` | string | Partition key (same as `id`). |
