# Service Testing Strategy – web

Summarize how this service validates behavior, referencing shared standards in `../../platform/TESTING.md`.

## Static Analysis
- **Linting**: ESLint with `react-hooks` and `refresh` plugins.
- **Type Checking**: TypeScript (`tsc -b`).

## Unit Testing
- **Status**: Not currently implemented.
- **Plan**: Add Vitest + React Testing Library for component testing.

## Integration/E2E Testing
- **Status**: Manual testing.
- **Plan**: Add Playwright for critical flows (Login -> Create Toy -> Create Trip).
