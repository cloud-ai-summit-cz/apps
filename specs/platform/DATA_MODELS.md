# Data Models

Document every persistent or transient data contract here. Treat this as the definitive schema catalog referenced by APIs, storage engines, and analytics jobs.

## Authoritative Principles
- **Single source of truth**: schemas here must match code and migrations.
- **Versioning**: use semantic versioning for breaking changes and note migration steps.
- **Specification by Example**: accompany each schema with realistic payload examples.

## Schema Inventory
| Name | Type | Partition Key / Primary Key | Description | Version |
| --- | --- | --- | --- | --- |
| Principal | Pydantic model | N/A | Authenticated caller (user or system) | 1.0.0 |
| Toy | Cosmos document | toy_id | Registered toy, owned by Entra user | 1.0.0 |
| Trip | Cosmos document | trip_id | Single-destination trip and gallery | 1.0.0 |

## Detailed Schemas

### Principal
High-level description of user and system principals; see auth implementation for exact fields.

### Toy
Summarize the Toy schema described in current code and `docs/DATA_MODELS.md` (id, owner_oid, name, description, avatar_blob_name, timestamps). Add concrete JSON examples as the model stabilizes.

### Trip
Summarize the Trip and GalleryImage schemas (trip id, toy reference, owner_oid, destination, status, gallery entries, timestamps). Add concrete JSON examples as the model stabilizes.

Extend with additional models (Add-On, Story, Location) as they are implemented.
