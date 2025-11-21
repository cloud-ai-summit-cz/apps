# Service Data Models – toy

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| Toy | Cosmos document / Pydantic model | toy service | Code + platform DATA_MODELS | 1.0.0 |

## Detailed Schemas

### Toy (Resource)
The complete representation of a registered Toy.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Unique toy identifier. |
| `owner_oid` | string | Entra object ID of the owner. |
| `name` | string | Display name of the toy (1-100 chars). |
| `description` | string? | Optional description or backstory (max 500 chars). |
| `avatar_blob_name` | string? | Internal blob storage reference for the avatar. |
| `has_avatar` | boolean | Indicates if toy has an avatar image. |
| `created_at` | datetime | Registration timestamp (UTC). |
| `updated_at` | datetime | Last modification timestamp (UTC). |

### ToyCreate (Request)
Payload for creating a new toy.

| Field | Type | Description |
| --- | --- | --- |
| `name` | string | Display name of the toy. |
| `description` | string? | Optional description. |
| `id` | UUID? | Optional explicit ID (used for imports). |

### ToyUpdate (Request)
Payload for partial updates.

| Field | Type | Description |
| --- | --- | --- |
| `name` | string? | New display name. |
| `description` | string? | New description. |

### ToyDocument (Storage)
Cosmos DB representation. Extends `Toy`.

| Field | Type | Description |
| --- | --- | --- |
| `toy_id` | string | Partition key (same as `id`). |
