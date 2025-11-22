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
- **Access Control**: Nginx must validate the presence of a valid session (e.g., cookie) before forwarding to the internal collector.
- **Rate Limiting**: Apply rate limits to this endpoint to prevent DoS attacks on the telemetry infrastructure.
