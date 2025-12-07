# Agent Service Testing Strategy

Summarize how this service validates behavior, referencing `../../platform/TESTING.md`.

## Test Matrix
| Layer | Tools | Scope | Owner |
| --- | --- | --- | --- |
| Unit | pytest | Prompt construction, tool selection, rate limiting | Service team |
| Integration | pytest + downstream stubs/live | Chat turn hitting toy/trip/story/geo/addon; ownership enforcement; SSE streaming | Platform QA |
| Contract | OpenAPI/AsyncAPI lint | Chat endpoints (REST/SSE) and tool event schemas | Service team |

## Scenarios
- Chat request returns location/status by invoking Geo/Trip with caller token.
- Mutating action (order add-on) requires owner token and results in downstream call.
- Prompt-injection attempt is neutralized (tool allow-list enforced).
- Session persistence: last N turns stored and retrievable; older turns trimmed.

## Environments
- Local: downstream services mocked; Azure OpenAI responses recorded or stubbed.
- CI: Integration uses staging endpoints with dedicated tenant where possible; fallback to mocks if unavailable.
- Staging/Prod: Synthetic chat smoke exercises read-only flow.

## Quality Gates
- Required CI: lint, unit, contract; integration required when staging is reachable.
- Waivers for integration or OpenAI-dependent tests must be documented with follow-up issue.