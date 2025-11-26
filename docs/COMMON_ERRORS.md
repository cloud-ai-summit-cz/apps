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

---

## Azure Monitor / OTEL Collector

### OTEL Collector 401 Unauthorized with App Insights DisableLocalAuth=true

**Symptoms:**
- OTEL Collector starts successfully, no errors in logs
- Traces/metrics appear in Aspire Dashboard (via OTLP exporter)
- No data appears in Azure Application Insights
- App Insights returns `401 Authentication Required` (visible in debug logs if enabled)

**Root Cause:**
When Application Insights has `DisableLocalAuth: true` (recommended for security), connection string authentication is blocked. The OTEL Collector must use Azure AD (Entra ID) authentication via the `azureauthextension`.

**Solution:**

1. **Use OTEL Collector version 0.140.1+** (or 0.139.0+) which includes native `azureauthextension` support for `azuremonitor` exporter.

2. **Configure `azureauthextension` with the required `scopes`:**

```yaml
extensions:
  azureauth:
    # CRITICAL: scopes must be specified!
    scopes:
      - https://monitor.azure.com/.default
    workload_identity:
      client_id: ${env:AZURE_CLIENT_ID}
      tenant_id: ${env:AZURE_TENANT_ID}
      federated_token_file: /var/run/secrets/azure/tokens/azure-identity-token

exporters:
  azuremonitor:
    connection_string: ${env:APPLICATIONINSIGHTS_CONNECTION_STRING}
    auth:
      authenticator: azureauth

service:
  extensions: [health_check, azureauth]  # azureauth must be listed
  pipelines:
    traces:
      exporters: [azuremonitor]
```

3. **Ensure Workload Identity is configured:**
   - AKS cluster must have Workload Identity enabled
   - Managed Identity with `Monitoring Metrics Publisher` role on App Insights
   - Federated credential configured for the service account
   - Pod labeled with `azure.workload.identity/use: "true"`
   - Environment variables `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` injected

**Common Pitfalls:**
- **Missing `scopes`**: Without `scopes: [https://monitor.azure.com/.default]`, the extension doesn't know what token to request
- **Wrong collector version**: Versions before 0.139.0 don't have `azureauthextension` support in `azuremonitor` exporter
- **Extension not in service.extensions**: The `azureauth` extension must be listed in `service.extensions` to be started
- **Federated token file path**: AKS injects the token at `/var/run/secrets/azure/tokens/azure-identity-token`

**References:**
- [PR #41107: azuremonitor authenticator support](https://github.com/open-telemetry/opentelemetry-collector-contrib/pull/41107)
- [azureauthextension documentation](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/azureauthextension)
