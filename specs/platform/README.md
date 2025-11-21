# Platform-Level Specifications

Use this folder for documentation that spans multiple services within this monorepo. Keep it lightweight—only add documents when a contract or decision truly applies to more than one service.

## Contents
- `ARCHITECTURE.md`: System context, shared diagrams, integration boundaries, and cross-cutting concerns.
- `DATA_MODELS.md`: Canonical schemas for events, shared tables, or reusable models.
- `OBSERVABILITY.md`: Organization-wide instrumentation and telemetry guidance.
- `TESTING.md`: Baseline testing expectations every service must meet.
- `DEPLOYMENT.md`: Release workflow, environment definitions, and compliance requirements.
- `SECURITY.md`: Shared security posture, control requirements, scanning expectations, and incident response guidance.

See existing `docs/*.md` files for initial content that should be migrated or referenced into these platform specs.
