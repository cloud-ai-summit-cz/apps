# Add-On Service Contracts

- **REST**
  - `POST /trips/{tripId}/addons`: Create an add-on order (idempotent via `Idempotency-Key` header).
  - `GET /trips/{tripId}/addons`: List orders for a trip (owner-scoped).
  - `GET /addons/{orderId}`: Fetch single order by id.
- **Messaging**
  - Service Bus queue `addon-fulfill`: payload `{ ownerId, tripId, orderId, addonType, mediaStyle?, correlationId }` produced by API; consumed by fulfillment worker.
  - Worker sends gallery update to Trip Service via authenticated REST call.

OpenAPI/AsyncAPI specifications will be added after endpoints stabilize.