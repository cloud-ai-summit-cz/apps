# Service Architecture Snapshot – web

Provide a focused view of how this service fits into the broader system while inheriting global context from `../../platform/ARCHITECTURE.md`.

## Context
- **Type**: Single Page Application (SPA).
- **Role**: Primary user interface for the Toy & Trip management system.
- **Users**: End users (toy owners) and Admins.

## Technology Stack
- **Framework**: React 18 + Vite.
- **Language**: TypeScript.
- **Styling**: Tailwind CSS.
- **Routing**: React Router v7.
- **Auth**: MSAL Browser (`@azure/msal-browser`, `@azure/msal-react`).

## Component Diagram
- **Client**: Browser running the React app.
- **CDN/Server**: Nginx container serving static assets.
- **Backends**:
  - `toy-service` (REST)
  - `trip-service` (REST)
  - `demo-data-init` (REST)
- **Identity Provider**: Microsoft Entra ID (OIDC/OAuth2).

## Configuration Strategy
- **Build-time**: `VITE_*` environment variables.
- **Runtime**: `window.ENV_CONFIG` injected via `env-config.js` at container startup.
  - Allows the same Docker image to be promoted across environments (dev, staging, prod) without rebuilding.

## Key Flows
1.  **Login**: Redirects to Entra ID -> Callback -> Token acquisition (stored in Session Storage).
2.  **API Calls**: Interceptor/Wrapper acquires Access Token silently and attaches `Authorization: Bearer ...` header.
3.  **Navigation**: Client-side routing via `AppRoutes.tsx`.
