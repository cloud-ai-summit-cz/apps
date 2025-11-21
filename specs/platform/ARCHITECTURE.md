# Architecture Overview

Capture system context, component boundaries, and key decisions that drive implementation.

## Context
- Problem statement and business drivers.
- User personas interacting with the system.

This project implements the "Stuffed Toy World Tour" demo described in `PRD.md` and `docs/REQUIREMENTS.md` (to be fully migrated here).

## Views
### System Context Diagram
Describe actors, upstream/downstream systems, and trust boundaries.
Attach Mermaid or Draw.io links.

### Container / Service View
| Component | Responsibility | Tech Stack | Deployment Target | Owners |
| --- | --- | --- | --- | --- |
| toy | Manage toy profiles, avatars, and metadata | Python / FastAPI | AKS | TODO |
| trip | Manage trips and galleries | Python / FastAPI | AKS | TODO |
| demo-data-init | Seed demo toys/trips/media | Python | AKS Job | TODO |
| web | SPA frontend consuming backend APIs | React + Vite | AKS / Nginx | TODO |
| otel-collector | Telemetry aggregation and routing | OpenTelemetry | AKS | Platform |
| aspire-dashboard | Telemetry visualization (Dev/Staging) | .NET Aspire | AKS | Platform |
| addon | Add-on ordering and fulfillment | Planned | AKS | TODO |
| geo | Location + live stream service | Planned | AKS | TODO |
| story | Batch story composer | Planned | AKS | TODO |
| agent | Chat backend orchestrating MCP tools | Planned | AKS | TODO |
| demo-location | Location simulator | Planned | AKS | TODO |
| demo-media | Image generation simulator | Planned | AKS | TODO |

### Data Flow
Outline event streams, API calls, or batch processes.
Reference `DATA_MODELS.md` entries.

## Cross-Cutting Concerns
- Security posture (authn/authz, data classification).
- Performance characteristics (latency targets, scaling strategy).
- Resilience (retry/backoff, circuit breakers, chaos testing).

## Dependencies
List third-party services, shared platforms, and integration contracts.

## Specification by Example
Include scenarios illustrating architectural rules (e.g., failover, rate limiting).

## Decision References
Link to ADRs, RFCs, and implementation log entries governing architecture choices.
