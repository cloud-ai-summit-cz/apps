# Agent Service Contracts

- **REST/SSE**
  - `POST /chat`: Accepts `{ sessionId, message }`; responds with streamed SSE chunks or full JSON depending on `Accept`.
  - `GET /sessions/{sessionId}`: Return persisted turns (owner-scoped).
  - `POST /sessions/{sessionId}/messages`: Append message and respond with assistant reply.
- **Tool calls (downstream)**
  - Uses existing Toy/Trip/Story/Geo/Addon REST contracts; caller token forwarded.
- **Messaging (optional)**
  - Service Bus topic `agent-tool-events`: async tool completions `{ sessionId, tool, status, resultSummary }`.

OpenAPI/AsyncAPI specs will be added once streaming contract is finalized.