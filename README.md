# apps

1. **Resource group** – Create the target Azure resource group
2. **Managed identity** – Create a managed identity (ideally outside that group) and grant it the Owner role on the resource group.
3. **Federation** – Configure workload identity federation for that managed identity against your forked GitHub repo.
4. **Core GitHub secrets** – Add `AZURE_CLIENT_ID`, `AZURE_OBJECT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` and `LETS_ENCRYPT_EMAIL` under *Settings → Secrets and variables → Actions*.
5. **Optional data access** – If you need dev access to data resources, add your user object ID as `AZURE_DEVELOPER_OBJECT_ID`.
6. **ArgoCD repo token** – Create a fine-grained PAT with `Contents` read-only access and store it as `ARGOCD_REPO_TOKEN`.
7. **Entra app registration** – Create the app, set SPA redirect URIs under *Authentication → Single-page application* (`http://localhost:3000`, `http://localhost:3000/auth/callback`, `https://appdemo-eniwvl.swedencentral.cloudapp.azure.com`), then save its scope (e.g., `api://5163cc2b-3d50-4278-8fbc-c13f3f0de588`) in `APP_ID_URI`.
8. **Managed Gateway preview** – Register the AKS Managed Gateway API feature with `az feature register --namespace Microsoft.ContainerService --name ManagedGatewayAPIPreview` before deploying infra.