# Service Deployment Plan – web

Describe how this service moves from commit to production, referencing shared workflows in `../../platform/DEPLOYMENT.md`.

## Build Pipeline
1.  **Install**: `npm install`
2.  **Type Check**: `npm run build` (runs `tsc -b && vite build`)
3.  **Artifact**: Static files in `dist/` folder.
4.  **Containerize**:
    - Base Image: `nginx:alpine`
    - Copy `dist/` to `/usr/share/nginx/html`
    - Copy `nginx.conf`
    - Copy `docker-entrypoint.sh`

## Runtime Configuration
The application uses the **"Build once, deploy anywhere"** pattern.
- **Mechanism**: `docker-entrypoint.sh` reads environment variables (`TOY_SERVICE_URL`, etc.) and writes them to `env-config.js` in the Nginx html root.
- **Client**: `apiConfig.ts` reads from `window.ENV_CONFIG` first, falling back to `import.meta.env`.

## Environments
| Env | URL | Config Source |
| --- | --- | --- |
| Local | `http://localhost:3000` | `.env` / `vite.config.ts` |
| Staging | `https://web-staging...` | Helm values -> Pod Env Vars |
| Prod | `https://web-prod...` | Helm values -> Pod Env Vars |
