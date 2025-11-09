# apps

1. Create resource group in Azure
2. Create managed identity in Azure (preferably outside of this resource group) and give it Owner role for our resource group
3. Configure identity federation for this identity pointing to your forked GitHub repository
4. In you GitHub repository configure as secret (Settings -> Secrets and variables -> Actions -> Repository secrets) your managed identity `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID`
5. ArgoCD in cluster need to access our private repo. Generate Personal Access Token (Profile -> Personal access tokens -> Fine-grained tokens) in GitHub with `Contents` read-only permission. Add it as `ARGOCD_REPO_TOKEN` secret in GitHub repository.