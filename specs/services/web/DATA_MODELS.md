# Service Data Models – web

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
The web service mirrors the data models of the backend services it consumes. It does not own persistent data but defines TypeScript interfaces for type safety.

| Name | Type | Source of Truth | Location |
| --- | --- | --- | --- |
| `Toy` | TypeScript Interface | `toy-service` | `src/types/toy.ts` |
| `Trip` | TypeScript Interface | `trip-service` | `src/types/trip.ts` |
| `GalleryImage` | TypeScript Interface | `trip-service` | `src/types/trip.ts` |

## State Management
- **Local State**: React `useState` / `useReducer` for form inputs and UI toggles.
- **Server State**: Fetched on mount via `useEffect` (no global cache like React Query currently implemented).
- **Auth State**: Managed by `MsalProvider` context.
