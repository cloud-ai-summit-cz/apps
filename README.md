# Cloud and AI summit 2025 Czech - apps demo

## Setup instructions

> **Tip:** These commands can be run from [Azure Cloud Shell](https://shell.azure.com) (Bash) which has `az` and `gh` CLI pre-installed.

### Prerequisites

Set these variables first (adjust values for your environment):

```bash
# Azure
SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="appdemo-rg"
LOCATION="swedencentral"
IDENTITY_NAME="appdemo-deploy-identity"

# GitHub (your forked repo)
GITHUB_REPO="<your-org>/apps"

# App registration
APP_NAME="ToyTrips"
PRODUCTION_URL="https://appdemo-xxxxx.swedencentral.cloudapp.azure.com"  # Update after infra deploy
```

---

### 1. Resource group

Create the target Azure resource group.

<details>
<summary>CLI commands</summary>

```bash
az account set --subscription "$SUBSCRIPTION_ID"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
```

</details>

---

### 2. Managed identity

Create a managed identity (ideally outside that group) and grant it the Owner role on the resource group.

<details>
<summary>CLI commands</summary>

```bash
# Create identity (in a separate persistent RG if preferred)
az identity create --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"

# Get IDs
CLIENT_ID=$(az identity show -n "$IDENTITY_NAME" -g "$RESOURCE_GROUP" --query clientId -o tsv)
OBJECT_ID=$(az identity show -n "$IDENTITY_NAME" -g "$RESOURCE_GROUP" --query principalId -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Assign Owner role on the resource group
az role assignment create \
  --assignee-object-id "$OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role Owner \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# Output values (save these for GitHub secrets)
echo "AZURE_CLIENT_ID=$CLIENT_ID"
echo "AZURE_OBJECT_ID=$OBJECT_ID"
echo "AZURE_TENANT_ID=$TENANT_ID"
```

</details>

---

### 3. Federation

Configure workload identity federation for that managed identity against your forked GitHub repo.

<details>
<summary>CLI commands</summary>

```bash
# Federation for main branch
az identity federated-credential create \
  --name "github-main" \
  --identity-name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:${GITHUB_REPO}:ref:refs/heads/main" \
  --audiences "api://AzureADTokenExchange"

# Optional: Add federation for pull requests if needed
az identity federated-credential create \
  --name "github-pr" \
  --identity-name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:${GITHUB_REPO}:pull_request" \
  --audiences "api://AzureADTokenExchange"
```

</details>

---

### 4. Core GitHub secrets

Add `AZURE_CLIENT_ID`, `AZURE_OBJECT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` and `LETS_ENCRYPT_EMAIL` under *Settings → Secrets and variables → Actions*.

<details>
<summary>CLI commands (requires gh CLI)</summary>

```bash
# Authenticate GitHub CLI (device code flow)
gh auth login

# Set secrets
gh secret set AZURE_CLIENT_ID --body "$CLIENT_ID" --repo "$GITHUB_REPO"
gh secret set AZURE_OBJECT_ID --body "$OBJECT_ID" --repo "$GITHUB_REPO"
gh secret set AZURE_TENANT_ID --body "$TENANT_ID" --repo "$GITHUB_REPO"
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" --repo "$GITHUB_REPO"
gh secret set AZURE_RESOURCE_GROUP --body "$RESOURCE_GROUP" --repo "$GITHUB_REPO"
gh secret set LETS_ENCRYPT_EMAIL --body "your-email@example.com" --repo "$GITHUB_REPO"
```

</details>

---

### 5. Optional data access

If you need dev access to data resources, add your user object ID as `AZURE_DEVELOPER_OBJECT_ID`.

<details>
<summary>CLI commands</summary>

```bash
# Get your own user object ID
DEV_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
echo "AZURE_DEVELOPER_OBJECT_ID=$DEV_OBJECT_ID"

# Set as GitHub secret
gh secret set AZURE_DEVELOPER_OBJECT_ID --body "$DEV_OBJECT_ID" --repo "$GITHUB_REPO"
```

</details>

---

### 6. ArgoCD repo token

Create a fine-grained PAT with `Contents` read-only access and store it as `ARGOCD_REPO_TOKEN`.

<details>
<summary>Instructions</summary>

**Manual step** – GitHub doesn't allow PAT creation via CLI for security reasons.

1. Go to [GitHub → Settings → Developer settings → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Click **Generate new token**
3. Set:
   - **Token name:** `argocd-repo-access`
   - **Expiration:** 90 days (or custom)
   - **Repository access:** Only select repositories → select your fork
   - **Permissions:** Contents → Read-only
4. Generate and copy the token

```bash
# Then set as secret
gh secret set ARGOCD_REPO_TOKEN --body "<your-pat>" --repo "$GITHUB_REPO"
```

</details>

---

### 7. Entra app registration

Create the app, set SPA redirect URIs under *Authentication → Single-page application*, configure app roles, and save its scope in `APP_ID_URI`.

<details>
<summary>CLI commands</summary>

```bash
# Create app registration
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --sign-in-audience AzureADMyOrg \
  --query appId -o tsv)
APP_OBJECT_ID=$(az ad app show --id "$APP_ID" --query id -o tsv)

echo "Created app: $APP_ID"

# Set identifier URI
az ad app update --id "$APP_ID" --identifier-uris "api://$APP_ID"

# Create app roles JSON
cat > /tmp/roles.json << 'EOF'
[
  {
    "allowedMemberTypes": ["User"],
    "displayName": "Toy Read/Write",
    "id": "11111111-1111-1111-1111-111111111111",
    "isEnabled": true,
    "description": "Read and write toy data",
    "value": "Toy.ReadWrite"
  },
  {
    "allowedMemberTypes": ["User"],
    "displayName": "Admin Full Access",
    "id": "22222222-2222-2222-2222-222222222222",
    "isEnabled": true,
    "description": "Full administrative access to all toys regardless of ownership",
    "value": "Admin.FullAccess"
  },
  {
    "allowedMemberTypes": ["Application"],
    "displayName": "System Service",
    "id": "33333333-3333-3333-3333-333333333333",
    "isEnabled": true,
    "description": "System service access for background operations",
    "value": "System.Service"
  }
]
EOF

# Add app roles
az ad app update --id "$APP_ID" --app-roles @/tmp/roles.json

# Configure SPA redirect URIs
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$APP_OBJECT_ID" \
  --headers "Content-Type=application/json" \
  --body "{\"spa\":{\"redirectUris\":[\"http://localhost:3000\",\"http://localhost:3000/auth/callback\",\"$PRODUCTION_URL\"]}}"

# Create service principal
SP_OBJECT_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)

echo "Service Principal created: $SP_OBJECT_ID"

# Set GitHub secret
gh secret set APP_ID_URI --body "api://$APP_ID" --repo "$GITHUB_REPO"

echo "APP_ID_URI=api://$APP_ID"
```

</details>

<details>
<summary>Assign users to app roles (optional)</summary>

```bash
# Get user's object ID
USER_EMAIL="user@yourdomain.com"
USER_OID=$(az ad user show --id "$USER_EMAIL" --query id -o tsv)

# Assign Toy.ReadWrite role (use the role ID from roles.json above)
ROLE_ID="11111111-1111-1111-1111-111111111111"

az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_OBJECT_ID/appRoleAssignedTo" \
  --headers "Content-Type=application/json" \
  --body "{\"principalId\":\"$USER_OID\",\"resourceId\":\"$SP_OBJECT_ID\",\"appRoleId\":\"$ROLE_ID\"}"

# For Admin role, use:
# ROLE_ID="22222222-2222-2222-2222-222222222222"
```

</details>

---

### 8. Managed Gateway preview

Register the AKS Managed Gateway API feature before deploying infra.

<details>
<summary>CLI commands</summary>

```bash
az feature register --namespace Microsoft.ContainerService --name ManagedGatewayAPIPreview

# Check registration status (may take a few minutes)
az feature show --namespace Microsoft.ContainerService --name ManagedGatewayAPIPreview --query properties.state -o tsv

# Once registered, refresh the provider
az provider register --namespace Microsoft.ContainerService
```

</details>

## Demo flow
1. Discuss **specs-driven development** and point to [https://github.com/tkubica12/gh-copilot-constitution](https://github.com/tkubica12/gh-copilot-constitution) with our constitution, guidelines, spec templates and so on.

Use Copilot Space to work on product requirements with context from one or more repositories and no IDE needed.

```
I want to create PRD for my idea - company that sells trip for rich people toys. They take them to the place customer wants, send photos of toys, share stories, real time location and users can order experiences or accessories on the trip.
```

Showcase Copilot Spark for rapid prototyping by pasting your PRD to it.

Go to IDE and discuss GitHub Copilot agent mode.

Show resulting running application

More autonomy for agents demo - defer to agent, assign to agent, agent code review, AgentHQ

Automation in GitHub Actions demo: container builds, Bicep for IaC, bridge between IaC and Argo and Argo bootstrap, Argo to deploy Kubernetes objects

Authentication - using entra users, authorization roles, app registrations 

But what about background processes or microservices accessing Azure services such as Blob storage or Cosmos DB? Managed identities and federation advantages.

When we talk about security - let's review network protection for our services, what else can we do to enhance security even further?

Focus on Azure Kubernetes Service - node autoprovisioning, auth, security and how bundled all that under AKS Automatic

Observability with OpenTelemetry instrumentation - from quick Aspire dashboard to Azure services (Azure Monitor for Prometheus, Application Insights, Log Analytics, ...)

Future of ops with SRE agents helping with incidents and identifying issues