# Shared Security Standard

Use this document to capture security controls that every service in the monorepo must honor. Service-level `SECURITY.md` files should reference this baseline and document only additional, local requirements or exceptions.

## Threat Modeling Expectations
- Run lightweight threat modeling for major features (auth changes, public endpoints, new data flows).
- Capture assets and trust boundaries in `specs/platform/ARCHITECTURE.md` and service specs.

## Identity & Access
- Authentication: Entra ID JWTs validated by backend services.
- Authorization: Application roles/scopes (e.g., App.Access, System.Service, Toy.ReadWrite) with explicit 401 vs 403 handling.
- Secrets & tokens: Prefer Managed Identity; no long-lived secrets for Azure resources.

## Data Protection
- Private endpoints for sensitive data stores (Cosmos DB, Storage) where configured.
- No public blob URLs or SAS tokens for image access; access via authenticated service proxy endpoints only.
- **Telemetry**: Frontend telemetry must be sent via a secure reverse proxy (e.g., Nginx sidecar) that enforces authentication. Do not expose OTEL collectors directly to the public internet.

## Secure Coding & Dependencies
- Use language-appropriate security linters and dependency scanners.
- Log auth failures with structured reasons but avoid sensitive payloads.

## Incident Response & Compliance
- Capture auth failure metrics (auth_failures_total{reason}).
- Define on-call responsibilities and escalation paths in service runbooks.

## Specification by Example
Add shared scenarios such as: "Given an API call without a valid token, the service returns 401 and emits an auth_failures_total metric with reason=missing_token".
