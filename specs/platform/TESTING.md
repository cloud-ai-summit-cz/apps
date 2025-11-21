# Shared Testing Strategy

Define the organization-wide testing expectations that every service must follow before shipping.

## Test Pyramid Targets
| Layer | Goal | Tooling Baseline |
| --- | --- | --- |
| Unit | Fast feedback, run on PR | pytest, Jest/Vitest, etc. (optional for now) |
| Integration | Validate IO boundaries (DB, queues, external APIs) | pytest + real Azure resources (current focus) |
| Contract | Prevent breaking shared APIs/events | OpenAPI validation, future PACT style tests |
| E2E/UX | Verify critical journeys end-to-end | Browser tests (future) |

## Quality Gates
- Centralized integration tests under `src/integration-tests/` hitting real services and Azure resources.
- Authentication and authorization flows must be covered by tests.

## Tooling Matrix
Document shared configuration for pytest, Azure test credentials, and any local test harness in the repo.

## Specification by Example
Service-level `TESTING.md` files should reference this baseline and add details (fixtures, scenarios, coverage) unique to each service.
