# Agent Service Data Models

Capture schemas owned by this service. Link to shared definitions from `../../platform/DATA_MODELS.md` when referencing canonical models.

## Schema Inventory
| Name | Type | Owner | Source of Truth | Version |
| --- | --- | --- | --- | --- |
| ChatSession | Cosmos document | Agent Service | `chat_sessions` container (HPK `ownerId`, `sessionId`) | 1.0.0 |
| ToolInvocationLog | Cosmos document | Agent Service | `chat_sessions` container (same HPK) | 1.0.0 |

## Detailed Schemas

### ChatSession
- Purpose: Persist minimal conversation state and grounding references for ongoing chat.
- Storage: Cosmos DB `chat_sessions`; HPK `ownerId`, `sessionId` to isolate tenants and keep partitions bounded.
- Lifecycle: Created on first message; truncated to retain last N turns (e.g., 20) to stay within 2 MB limit.
- Sample payload:
```json
{
  "id": "session_abc",
  "ownerId": "<entra_oid>",
  "sessionId": "abc",
  "turns": [
    {"role": "user", "content": "Where is my toy?", "timestamp": "2025-12-07T21:00:00Z"},
    {"role": "assistant", "content": "Fluffy is in Prague...", "timestamp": "2025-12-07T21:00:02Z"}
  ],
  "grounding": {"tripId": "trip_123", "toyId": "toy_9"},
  "createdAt": "2025-12-07T21:00:00Z",
  "updatedAt": "2025-12-07T21:05:00Z"
}
```
- Validation: Enforce `ownerId`, `sessionId`; cap turns; redact secrets from user content if detected.

### ToolInvocationLog
- Purpose: Track downstream tool calls for auditability and retry.
- Fields: `tool`, `request`, `responseSummary`, `status`, `durationMs`, `traceId`.
- Stored alongside session in same HPK for co-located queries; rotate older entries to avoid partition bloat.