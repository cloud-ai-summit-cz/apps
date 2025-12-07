# Geo Service Testing Strategy

Summarize how this service validates behavior, referencing `../../platform/TESTING.md`.

## Test Matrix
| Layer | Tools | Scope | Owner |
| --- | --- | --- | --- |
| Unit | pytest | Payload validation, rate limiting, coordinate normalization | Service team |
| Integration | pytest + Cosmos/Service Bus + WebSocket client | Ingest message, persist, broadcast to WS, enforce auth | Platform QA |
| Contract | OpenAPI/AsyncAPI lint | REST/WebSocket/message schemas | Service team |

## Scenarios
- Ingest location for owned trip; latest location available via REST and broadcast over WebSocket.
- Reject ingestion for unauthorized principal; WebSocket without token fails.
- Backpressure handling: simulate slow client and ensure server drops oldest frames, not crashing.
- TTL enforcement: expired records not returned in history query.

## Environments
- Local: Cosmos emulator optional; WebSocket tests run against dev container; Service Bus emulator not available—use live dev namespace.
- CI: Integration hits staging resources with isolated partitions.
- Staging/Prod: Synthetic location publish post-deploy; WS smoke ensures broadcast.

## Quality Gates
- CI must run lint + unit + contract; integration required when staging resources available.
- Any skipped WebSocket tests must record reason and issue for follow-up.