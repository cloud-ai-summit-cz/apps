# Story Service Testing Strategy

Summarize how this service validates behavior, referencing `../../platform/TESTING.md`.

## Test Matrix
| Layer | Tools | Scope | Owner |
| --- | --- | --- | --- |
| Unit | pytest | Prompt assembly, input validation, idempotency guards | Service team |
| Integration | pytest + live Cosmos/Service Bus/OpenAI sandbox | Generate story for trip; enforce ownership; queue-triggered worker path | Platform QA |
| Contract | OpenAPI schema lint | Request/response shapes for `/stories` endpoints | Service team |

## Scenarios
- Create story for owned trip via REST and via queue worker.
- Enforce 401/403 on missing/foreign owner tokens.
- Retry and surface errors when Azure OpenAI returns 429/5xx.
- Ensure generated story persists in Cosmos with correct HPK and is retrievable.

## Environments
- Local: OpenAI emulator or recorded responses; Cosmos emulator optional for fast feedback.
- CI: Uses staging Cosmos/Service Bus resources; stories written to non-prod partitions.
- Staging/Prod: Synthetic story generated post-deploy for smoke; cleared after verification.

## Quality Gates
- Required CI jobs: lint, unit, contract, integration (non-blocking if Azure sandbox unavailable but must report).
- Waivers: Any skipped integration must be justified in pipeline logs and tracked for follow-up.