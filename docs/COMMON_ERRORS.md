# Common Errors & Solutions

This document tracks recurring technical issues, pitfalls, and their solutions to help future development.

## Frontend / OpenTelemetry

### MSAL Breaks OpenTelemetry Trace Context (Zone.js)

**Symptoms:**
- Frontend traces are fragmented; API calls appear as root spans instead of children of the page load or user interaction span.
- `traceId` becomes `undefined` or changes unexpectedly after authentication calls.
- Logs show `contextLost: true` or similar behavior after `await msalInstance.acquireTokenSilent()`.

**Root Cause:**
The `@azure/msal-browser` library's internal promise handling (specifically around iframe polling for silent tokens) can break the `zone.js` execution context. Since OpenTelemetry Web SDK relies on `zone.js` to track the active span across async operations, the context is lost when the MSAL promise resolves.

**Solution:**
Use the "Capture and Restore" pattern in your API clients. Capture the active context *before* the MSAL call, and explicitly wrap the subsequent `fetch` (or async operation) in `context.with()`.

```typescript
import { context, trace } from '@opentelemetry/api';

// 1. Capture context BEFORE MSAL call
const parentContext = context.active();

// 2. Perform Auth (which breaks context)
const token = await this.getAccessToken();

// 3. Restore context explicitly
return context.with(parentContext, async () => {
  // Now this fetch will correctly inherit the parent span
  return fetch(url, { ... });
});
```

**Related Dependencies:**
- Ensure `zone.js` is compatible with your OpenTelemetry version. We found `zone.js@0.14.10` to be stable with `@opentelemetry/instrumentation-user-interaction`.
