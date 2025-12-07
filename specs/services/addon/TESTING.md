# Add-On Service Testing Strategy

Summarize how this service validates behavior, referencing `../../platform/TESTING.md`.

## Test Matrix
| Layer | Tools | Scope | Owner |
| --- | --- | --- | --- |
| Unit | pytest | Validation, idempotency key handling, status transitions | Service team |
| Integration | pytest + Cosmos/Service Bus/Storage + Trip stub | Place order, enqueue, fulfill, gallery update | Platform QA |
| Contract | OpenAPI/AsyncAPI lint | REST endpoints and queue message schema | Service team |

## Scenarios
- Create order for owned trip; idempotent on repeated idempotency key.
- Unauthorized caller cannot create/read other owner orders.
- Worker processes queue message, calls Demo Media, uploads to Storage, updates order and Trip gallery.
- Failure path marks order `failed` after retry budget and leaves error recorded.

## Environments
- Local: Cosmos emulator optional; queue interactions against dev Service Bus; Demo Media mocked.
- CI: Integration uses staging resources; isolation via unique `ownerId`/`tripId` per run.
- Staging/Prod: Synthetic order created post-deploy and verified fulfilled, then cleaned up.

## Quality Gates
- Required CI: lint, unit, contract; integration required when Service Bus/Storage available.
- Skipped integration must log reason and create follow-up issue.