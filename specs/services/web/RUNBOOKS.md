# Service Runbooks – web

Operational procedures for on-call engineers.

## Troubleshooting

### White Screen of Death / App Not Loading
1.  Check Browser Console for JS errors.
2.  Verify `env-config.js` loaded correctly in Network tab.
    - If missing or empty, check container logs for `docker-entrypoint.sh` errors.

### Login Loops / Auth Failures
1.  Clear Session Storage.
2.  Verify `MSAL_REDIRECT_URI` matches the current URL exactly.
3.  Check Entra ID App Registration redirect URIs.
4.  Check console for MSAL error codes (e.g., `interaction_required`).

### API Connection Errors
1.  Check Network tab for CORS errors.
2.  Verify `TOY_SERVICE_URL` and `TRIP_SERVICE_URL` in `window.ENV_CONFIG`.
3.  Ensure backend services are running and accessible from the browser.
