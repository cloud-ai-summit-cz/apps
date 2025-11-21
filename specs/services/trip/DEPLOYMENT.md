## Trip Service Deployment

The Trip Service is deployed as a FastAPI container behind the shared Gateway.

- Container image built from `src/services/trip`
- Exposed internally on `/trip` with HTTP port from settings
- Ingress:
  - Gateway HTTPRoute maps external `/api/trips` to internal `/trip`
