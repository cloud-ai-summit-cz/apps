@description('Prefix used for naming resources.')
param prefix string

@description('Object ID of the user (or managed identity later) that should have data-plane contributor access.')
param userObjectId string

@description('Location for all resources.')
param location string = resourceGroup().location

// Deterministic unique suffix seeded by subscription + prefix
var rawUnique = uniqueString(subscription().id, prefix)
// Replace digits with letters a-j to satisfy "letters only" requirement
var sanitizedUnique = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(rawUnique, '0', 'a'), '1', 'b'), '2', 'c'), '3', 'd'), '4', 'e'), '5', 'f'), '6', 'g'), '7', 'h'), '8', 'i'), '9', 'j')
var baseNameDash = '${prefix}-${sanitizedUnique}'
var baseNameNoDash = '${prefix}${sanitizedUnique}'

// Storage Account module (flattened path) - naming handled inside module
module storage 'modules/storageAccount.bicep' = {
  name: 'storageDeploy'
  params: {
    baseNameNoDash: baseNameNoDash
    baseNameDash: baseNameDash
    location: location
  }
}

// Cosmos DB serverless (SQL) module (flattened path) - naming handled inside module
module cosmos 'modules/cosmosSqlServerless.bicep' = {
  name: 'cosmosDeploy'
  params: {
    baseNameNoDash: baseNameNoDash
    baseNameDash: baseNameDash
    location: location
  }
}

// Storage RBAC assignments (standard Azure RBAC via Microsoft.Authorization)
var storageRbacAssignments = [
  {
    principalObjectId: userObjectId
    roleName: 'Storage Blob Data Contributor'
    storageAccountName: storage.outputs.storageAccountName
  }
]

module storageRbac 'modules/roleAssignments.bicep' = {
  name: 'storageRbacDeploy'
  params: {
    assignments: storageRbacAssignments
  }
}

// Cosmos DB data-plane RBAC assignments (Cosmos-specific via Microsoft.DocumentDB)
var cosmosRbacAssignments = [
  {
    principalObjectId: userObjectId
    roleName: 'Cosmos DB Built-in Data Contributor'
    // scope defaults to account level inside module
  }
]

module cosmosRbac 'modules/cosmosRoleAssignments.bicep' = {
  name: 'cosmosRbacDeploy'
  params: {
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    assignments: cosmosRbacAssignments
  }
}

output storageAccountId string = storage.outputs.storageAccountId
output cosmosAccountId string = cosmos.outputs.cosmosAccountId
output baseNameDash string = baseNameDash
output baseNameNoDash string = baseNameNoDash
