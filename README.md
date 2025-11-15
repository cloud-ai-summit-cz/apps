# apps

1. Create resource group in Azure
2. Create managed identity in Azure (preferably outside of this resource group) and give it Owner role for our resource group
3. Configure identity federation for this identity pointing to your forked GitHub repository
4. In you GitHub repository configure as secret (Settings -> Secrets and variables -> Actions -> Repository secrets) your managed identity `AZURE_CLIENT_ID`, `AZURE_OBJECT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and `LETS_ENCRYPT_EMAIL`
5. If you want to give access to data resources (database, storage) for development purposes, add you user object id to `AZURE_DEVELOPER_OBJECT_ID` GitHub secret
6. ArgoCD in cluster need to access our private repo. Generate Personal Access Token (Profile -> Personal access tokens -> Fine-grained tokens) in GitHub with `Contents` read-only permission. Add it as `ARGOCD_REPO_TOKEN` secret in GitHub repository.
7. Register application in Entra (no credentials needed) and store its scope (eg. api://5163cc2b-3d50-4278-8fbc-c13f3f0de588) in `APP_ID_URI` GitHub secret.
8. Register the AKS Managed Gateway API preview feature before deploying infrastructure (see below).

## Enable AKS Managed Gateway API Preview

The AKS cluster uses the Istio Managed Gateway API preview. Run the following commands **once per subscription** (Contributor or Owner role required):

```bash
az feature register --namespace Microsoft.ContainerService --name ManagedGatewayAPIPreview
az provider register --namespace Microsoft.ContainerService
```

Use `az feature list --namespace Microsoft.ContainerService --query "[?name=='Microsoft.ContainerService/ManagedGatewayAPIPreview'].properties.state" -o tsv` to verify the feature state is `Registered` before re-running the infra deployment.