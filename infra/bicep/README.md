# Environment Deployment (Storage + Cosmos + RBAC)

## Overview
Deploys a serverless Cosmos DB (SQL) account + database + container, a Storage Account (Blob), and assigns data-plane RBAC roles to a provided Entra ID object (user for now; later managed identities).

Resources:
- Storage Account: `st<prefix><random>` (public network access enabled, blob public access disabled)
- Cosmos DB Account (Serverless): `cos<prefix><random>` with one database and container
- Role Assignments: Storage Blob Data Contributor & Cosmos DB Built-in Data Contributor

Naming suffix derived from `uniqueString(subscription().id, prefix)` with digits mapped to letters (0→a ... 9→j) to satisfy letter-only requirement.

## Prerequisites
- Azure CLI logged in: `az login`
- Correct subscription selected: `az account set -s <subscriptionId>`

## Get Your Object ID
```pwsh
$objectId = az ad signed-in-user show --query id -o tsv
```

## Create Resource Group
```pwsh
$rg='rg-demo-bicep'
az group create -n $rg -l swedencentral
```

## Deploy
Update `infra/bicep/main.parameters.bicepparam` with your objectId.
```pwsh
az deployment group create -g $rg -f main.bicep -p main.parameters.bicepparam
```
Or override inline:
```pwsh
az deployment group create -g $rg -f main.bicep -p prefix='demo' userObjectId=$objectId location='swedencentral'
```

## Inspect Outputs
```pwsh
az deployment group show -g $rg -n main --query properties.outputs
```

## Delete (Destroy Environment)
Non-blocking delete:
```pwsh
az group delete -n $rg -y --no-wait
```
Blocking delete (wait until finished):
```pwsh
az group delete -n $rg -y
```

## Next Steps (Roadmap)
- Add Private Endpoints & set publicNetworkAccess to Disabled after approval.
- Add Diagnostic Settings module (Log Analytics + categories).
- Introduce Managed Identity module and extend `rbacAssignments`.
- Parameterize partition key & additional Cosmos containers.
- Optional IP firewall restriction prior to Private Endpoints.

## Notes
- Role assignment propagation may take up to ~60s before effective.
- Suffix transformation removes digits to satisfy naming convention request; storage account still allows numbers but we keep deterministic pattern.
