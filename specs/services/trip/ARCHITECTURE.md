## Trip Service Architecture

The Trip Service manages trips for toys and their photo galleries.

### Responsibilities

- Create and manage trips for a specific toy
- Store basic trip metadata (title, description, location, country_code)
- Persist gallery images for each trip in blob storage
- Enforce that only the toy owner can mutate a trip or its gallery

### HTTP Surface

- `POST /trip` – create trip for a toy (verifies toy ownership via Toy Service)
- `GET /trip` – list trips filtered by `toy_id` or `owner_oid`
- `GET /trip/{trip_id}` – get a single trip with embedded gallery
- `PATCH /trip/{trip_id}` – partial update of trip metadata
- `DELETE /trip/{trip_id}` – delete trip and all gallery images
- `POST /trip/{trip_id}/gallery` – upload new gallery image
- `GET /trip/{trip_id}/gallery/{image_id}` – stream gallery image
- `DELETE /trip/{trip_id}/gallery/{image_id}` – remove gallery image
