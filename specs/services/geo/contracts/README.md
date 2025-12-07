# Geo Service Contracts

- **REST**
  - `POST /trips/{tripId}/locations`: Ingest a location payload; idempotent via `capturedAt` per trip.
  - `GET /trips/{tripId}/locations/latest`: Return latest known location.
  - `GET /trips/{tripId}/locations?since=timestamp`: Optional bounded history within TTL.
- **WebSocket**
  - `/ws/trips/{tripId}`: Server pushes location frames `{ lat, lon, accuracyMeters, capturedAt, seq }`; token required on handshake.
- **Messaging**
  - Service Bus topic `geo-locations`: upstream simulator publishes `{ ownerId, tripId, lat, lon, capturedAt, correlationId }`; worker consumes via subscription.

Contracts to be formalized in OpenAPI/AsyncAPI once implementation stabilizes.