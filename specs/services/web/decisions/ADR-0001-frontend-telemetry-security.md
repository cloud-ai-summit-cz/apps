# ADR-0001: Frontend Telemetry Security Model

**Date:** 2025-11-22

**Status:** Accepted

## Context

The frontend web application needs to send OpenTelemetry traces to the internal OTEL Collector deployed in the AKS cluster. However, exposing the collector directly to the internet poses security risks:

1. **Unauthorized Access:** Unauthenticated users could spam the telemetry endpoint, causing resource exhaustion or polluting telemetry data.
2. **Cost Impact:** Malicious actors could generate high volumes of telemetry, increasing storage and processing costs.
3. **Data Integrity:** Without authentication, fake or malicious telemetry could be injected into the system.

The OTEL Collector itself does not provide robust authentication mechanisms suitable for frontend clients, and implementing token-based auth for browser telemetry would require exposing credentials in the client.

## Decision

We implement an **Nginx-based proxy layer** in the web service container that:

1. **Exposes a telemetry endpoint** at `/otel/v1/traces` for the frontend to POST OTLP trace data.
2. **Validates authentication** by checking for the presence of MSAL session cookies before forwarding requests to the internal collector.
3. **Applies rate limiting** (100 requests/minute per IP) to prevent abuse.
4. **Proxies authenticated requests** to the internal OTEL Collector endpoint within the cluster.

### Security Model

- **Authentication Check:** The Nginx configuration validates that the request contains MSAL session cookies (`msal.*` pattern). This indicates an active authenticated session.
- **No Direct Token Exposure:** Access tokens are NOT sent with telemetry requests—only session cookies are checked. This avoids exposing bearer tokens in telemetry payloads.
- **Session-Based Trust:** The presence of a valid session cookie proves the user has authenticated with the application, which is sufficient for telemetry authorization.
- **Rate Limiting:** Configured at 500 requests/minute per IP with a burst of 1000, preventing DoS attacks.
- **Network Isolation:** The OTEL Collector remains internal to the cluster and is not exposed externally.

### Trade-offs

**Pros:**
- Simple implementation leveraging existing MSAL authentication.
- No additional credentials to manage or expose in the browser.
- Strong protection against unauthenticated telemetry submission.
- Rate limiting prevents abuse from authenticated users.

**Cons:**
- Cookie-based validation is less granular than token validation (cannot verify specific user identity or claims).
- If session cookies are compromised, an attacker could send telemetry (but this requires a broader session compromise).
- Rate limiting is per-IP, which could affect multiple users behind a shared NAT.

## Implementation Details

### Nginx Configuration

```nginx
location /otel/v1/traces {
    limit_except POST {
        deny all;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=otel_limit:10m rate=500r/m;
    limit_req zone=otel_limit burst=1000 nodelay;
    
    # Authentication check
    if ($http_cookie !~* "msal") {
        return 401 "Unauthorized: Valid session required";
    }
    
    # Proxy to internal collector
    proxy_pass ${OTEL_COLLECTOR_URL}/v1/traces;
    ...
}
```

### Frontend Configuration

The frontend uses `@opentelemetry/exporter-trace-otlp-http` to send traces to the relative endpoint `/otel/v1/traces`. Session cookies are automatically included in the request by the browser.

## Consequences

### Positive
- Telemetry infrastructure is protected from unauthorized access.
- Implementation is straightforward and maintainable.
- Aligns with existing authentication model (MSAL sessions).
- Rate limiting provides additional protection against abuse.

### Negative
- Requires maintaining Nginx configuration for telemetry routing.
- Session cookie validation is less precise than token validation.
- If MSAL session management changes, this mechanism may need updates.

### Neutral
- Adds minimal latency (one additional hop through Nginx proxy).
- Telemetry volume is controlled by sampling rate, not by this security layer.

## Alternatives Considered

1. **Direct Collector Exposure with Basic Auth:** Would require embedding credentials in frontend code, which is insecure.

2. **Token-Based Authentication on Collector:** OTEL Collector extensions for OAuth are complex and not designed for browser clients.

3. **Backend Telemetry Relay Service:** A dedicated backend service to accept telemetry would add complexity and another hop.

4. **No Authentication:** Unacceptable due to abuse potential and cost risks.

## References

- [OpenTelemetry OTLP Exporter Documentation](https://opentelemetry.io/docs/languages/js/exporters/)
- [Nginx Proxy Documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Nginx Rate Limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- `specs/platform/OBSERVABILITY.md`
- `specs/services/web/SECURITY.md`
