# Service Security Notes – web

Detail the threat model and controls unique to this service. Align with global requirements from `../../platform/SECURITY.md`.

## Authentication
- **Protocol**: OIDC / OAuth 2.0 (Authorization Code Flow with PKCE).
- **Library**: MSAL Browser (`@azure/msal-browser`).
- **Storage**: `sessionStorage` (cleared on tab close, mitigates some XSS persistence risks vs localStorage).

## Authorization
- **Access Tokens**: Acquired for specific scopes (`api://.../App.Access`).
- **Bearer Tokens**: Sent in `Authorization` header for all backend requests.

## Content Security Policy (CSP)
- Currently relies on default Nginx settings.
- **Recommendation**: Implement strict CSP to prevent XSS, restricting `script-src` to self and trusted CDNs.

## CORS
- The web app is the **origin**. Backend services must allow this origin in their CORS configuration.

## Telemetry Security
- **Endpoint**: `/otel/v1/traces` is exposed by Nginx.
- **Access Control**: Nginx validates the Referer header to ensure requests originate from the same origin (see ADR-0001).
- **Rate Limiting**: 500 requests/minute per IP with burst of 1000 to prevent DoS attacks.
- **Network Isolation**: OTEL Collector remains internal to the cluster, not exposed externally.
- **Details**: See [ADR-0001: Frontend Telemetry Security Model](decisions/ADR-0001-frontend-telemetry-security.md)
