# Service Observability Plan – trip

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **trips_viewed_total** (counter, dimensions: user_id, trip_id, is_admin): Trip detail views
- **trips_created_total** (counter, dimensions: user_id, destination): New trip creations
- **gallery_images_viewed_total** (counter, dimensions: trip_id, media_type, is_admin): Gallery image views

## Logs
- Ensure `user_id`, `trip_id`, and `destination` are included in structured logs.

## Traces
- **trip.create:** Trip creation (user validation, destination lookup, storage)
- **trip.gallery.upload:** Gallery image upload (blob storage, metadata update)
- **Filtering:** Low-level ASGI spans (`http send`, `http receive`) are filtered out to reduce noise during image streaming.

## Alerts
- Alert on high failure rate for `trip.create`.
