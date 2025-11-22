# Toy Service Web Application

Modern React frontend for the Toy Service application with Microsoft Entra ID authentication.

## Features

- Microsoft Entra ID (Azure AD) authentication using MSAL
- Browse toy catalog with grid layout
- View toy details
- Edit toy information (name, description)
- Upload/delete toy avatars
- Responsive design with Tailwind CSS
- TypeScript for type safety
- OpenTelemetry distributed tracing with automatic instrumentation

## Prerequisites

- Node.js 18+ and npm
- Toy Service backend running on http://localhost:8001
- Microsoft Entra ID app registration configured

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. (Optional) Create `.env` file for custom configuration:
```bash
VITE_TOY_SERVICE_URL=http://localhost:8001
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Authentication Configuration

The app is configured to use the following Entra ID application:
- **Client ID**: 64b74c90-ecd0-4404-984b-7919b5d56ac1
- **Tenant ID**: 6ce4f237-667f-43f5-aafd-cbef954adf97
- **Scope**: api://64b74c90-ecd0-4404-984b-7919b5d56ac1/App.Access

To modify these settings, edit `src/config/authConfig.ts`.

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── config/          # Configuration files (auth, API)
├── components/      # Reusable components
├── pages/           # Page components
├── routes/          # Route configuration
├── services/        # API clients
├── types/           # TypeScript type definitions
└── main.tsx         # Application entry point
```

## Environment Variables

- `VITE_TOY_SERVICE_URL` - Backend API base URL (default: http://localhost:8001)

## OpenTelemetry Observability

The web application is instrumented with OpenTelemetry for distributed tracing:

### Automatic Instrumentation

- **Document Load**: Traces page load performance and Core Web Vitals
- **Fetch Requests**: Automatically traces all HTTP requests with trace context propagation
- **User Interactions**: Captures click and submit events

### Security Model

Telemetry is sent to `/otel/v1/traces`, which is proxied by Nginx to the internal OTEL Collector. The endpoint requires a valid MSAL session (authenticated users only) and enforces rate limiting (100 requests/minute per IP).

See [ADR-0001](../../specs/services/web/decisions/ADR-0001-frontend-telemetry-security.md) for details on the security model.

### Custom Instrumentation

Use the telemetry utility for manual spans:

```typescript
import { withSpan, addSpanAttributes } from './utils/telemetry';

// Wrap operations in custom spans
await withSpan('View Trip Gallery', async (span) => {
  const images = await tripApiClient.getGalleryImages(tripId);
  span.addEvent('Images loaded', { count: images.length });
  return images;
}, { trip_id: tripId, user_id: userId });

// Add attributes to the current span
addSpanAttributes({
  user_id: user.oid,
  is_admin: user.roles.includes('Admin'),
});
```

### Configuration

Telemetry configuration is in `src/config/telemetryConfig.ts`. Sampling rate is configurable:
- **Development/Staging**: 100% sampling
- **Production**: 10% sampling (configurable via environment)

### Runtime Configuration

Docker deployment supports these environment variables:
- `OTEL_COLLECTOR_URL` - Internal OTEL Collector endpoint (default: http://otel-collector:4318)
- `ENVIRONMENT` - Deployment environment (development/staging/production)
- `SERVICE_VERSION` - Service version for telemetry tagging
