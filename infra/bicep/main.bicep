@description('Prefix used for naming resources.')
param prefix string

@description('Object ID of the user that should have data-plane access (eg. developer for testing - not for production)')
param userObjectId string = ''

@description('Object ID of managed identity that Bicep runs on so it can access AKS to bootstrap ArgoCD')
param gitHubWorkflowIdentityObjectId string = ''

@description('Location for all resources.')
param location string = resourceGroup().location

@description('Enable private endpoints for Cosmos DB, Storage, and ACR.')
param enablePrivateEndpoints bool = false

@description('Enable public network access for Cosmos DB, Storage, and ACR.')
param enablePublicAccess bool = true

// Deterministic unique suffix seeded by subscription + prefix (6 characters)
var rawUnique = uniqueString(subscription().id, prefix)
// Replace digits with letters a-j to satisfy "letters only" requirement, then take first 6 chars
var sanitizedUnique = substring(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(rawUnique, '0', 'a'), '1', 'b'), '2', 'c'), '3', 'd'), '4', 'e'), '5', 'f'), '6', 'g'), '7', 'h'), '8', 'i'), '9', 'j'), 0, 6)
var baseNameDash = '${prefix}-${sanitizedUnique}'
var baseNameNoDash = '${prefix}${sanitizedUnique}'

// Networking - VNet, NAT Gateway, Subnets, Private DNS Zones
module networking 'modules/networking.bicep' = {
  name: 'networkingDeploy'
  params: {
    baseNameDash: baseNameDash
    location: location
  }
}

// User-Assigned Managed Identities for AKS
resource aksClusterIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseNameDash}-cluster'
  location: location
}

resource aksKubeletIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseNameDash}-kubelet'
  location: location
}

// Azure Container Registry
module acr 'modules/acr.bicep' = {
  name: 'acrDeploy'
  params: {
    baseNameNoDash: baseNameNoDash
    baseNameDash: baseNameDash
    location: location
    publicNetworkAccess: enablePublicAccess ? 'Enabled' : 'Disabled'
    // privateEndpointSubnetId: enablePrivateEndpoints ? networking.outputs.privateEndpointsSubnetId : ''
    // privateDnsZoneId: enablePrivateEndpoints ? networking.outputs.acrDnsZoneId : ''
  }
}

// Built-in role definition IDs
var roleDefinitions = {
  AcrPull: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  ManagedIdentityOperator: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'f1a07417-d97a-45cb-824c-7a7467783830')
  NetworkContributor: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d97b98b-1d4f-4787-a291-c67834d212e7')
  StorageBlobDataContributor: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  AksRbacClusterAdmin: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b')
}

// Special: Managed Identity Operator needs to be scoped to the kubelet identity resource
resource managedIdentityOperatorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aksKubeletIdentity
  name: guid(aksKubeletIdentity.id, aksClusterIdentity.id, roleDefinitions.ManagedIdentityOperator)
  properties: {
    roleDefinitionId: roleDefinitions.ManagedIdentityOperator
    principalId: aksClusterIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// AKS Automatic Cluster
module aks 'modules/aksAutomatic.bicep' = {
  name: 'aksDeploy'
  params: {
    baseName: baseNameDash
    location: location
    clusterSubnetId: networking.outputs.aksNodesSubnetId
    apiServerSubnetId: networking.outputs.aksApiSubnetId
    clusterIdentityId: aksClusterIdentity.id
    clusterIdentityPrincipalId: aksClusterIdentity.properties.principalId
    kubeletIdentityId: aksKubeletIdentity.id
    kubeletIdentityPrincipalId: aksKubeletIdentity.properties.principalId
  }
  dependsOn: [
    managedIdentityOperatorAssignment
  ]
}

// Storage Account module (flattened path) - naming handled inside module
module storage 'modules/storageAccount.bicep' = {
  name: 'storageDeploy'
  params: {
    baseNameNoDash: baseNameNoDash
    baseNameDash: baseNameDash
    location: location
    publicNetworkAccess: enablePublicAccess ? 'Enabled' : 'Disabled'
    privateEndpointSubnetId: enablePrivateEndpoints ? networking.outputs.privateEndpointsSubnetId : ''
    privateDnsZoneId: enablePrivateEndpoints ? networking.outputs.blobDnsZoneId : ''
  }
}

// Cosmos DB serverless (SQL) module (flattened path) - naming handled inside module
module cosmos 'modules/cosmosSqlServerless.bicep' = {
  name: 'cosmosDeploy'
  params: {
    baseNameNoDash: baseNameNoDash
    baseNameDash: baseNameDash
    location: location
    publicNetworkAccess: enablePublicAccess ? 'Enabled' : 'Disabled'
    privateEndpointSubnetId: enablePrivateEndpoints ? networking.outputs.privateEndpointsSubnetId : ''
    privateDnsZoneId: enablePrivateEndpoints ? networking.outputs.cosmosDnsZoneId : ''
  }
}

// =============================================================================
// RBAC Assignments - Flat List Approach
// All Azure RBAC role assignments in one place for easy management
// =============================================================================

// Build flat list of all RBAC assignments
var allRbacAssignments = [
  // AKS Kubelet Identity -> ACR Pull (for pulling container images)
  {
    principalId: aksKubeletIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleDefinitions.AcrPull
  }
  // AKS Cluster Identity -> Network Contributor (for VNet integration)
  {
    principalId: aksClusterIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleDefinitions.NetworkContributor
  }
  // Human User -> Storage Blob Data Contributor (optional)
  !empty(userObjectId) ? {
    principalId: userObjectId
    principalType: 'User'
    roleDefinitionId: roleDefinitions.StorageBlobDataContributor
  } : null
  // Human User -> AKS RBAC Cluster Admin (optional)
  !empty(userObjectId) ? {
    principalId: userObjectId
    principalType: 'User'
    roleDefinitionId: roleDefinitions.AksRbacClusterAdmin
  } : null
  // GitHub Workflow Identity -> AKS RBAC Cluster Admin (optional)
  !empty(gitHubWorkflowIdentityObjectId) ? {
    principalId: gitHubWorkflowIdentityObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleDefinitions.AksRbacClusterAdmin
  } : null
]

// Filter out null entries (from optional assignments)
var rbacAssignments = filter(allRbacAssignments, assignment => assignment != null)

// Deploy all RBAC assignments via module
module rbac 'modules/rbacAssignments.bicep' = {
  name: 'rbacDeploy'
  params: {
    assignments: rbacAssignments
  }
  dependsOn: [
    managedIdentityOperatorAssignment
  ]
}

// =============================================================================
// Cosmos DB RBAC (separate - uses different API)
// =============================================================================

var cosmosRbacAssignments = [
  {
    principalObjectId: userObjectId
    roleName: 'Cosmos DB Built-in Data Contributor'
  }
]

module cosmosRbac 'modules/cosmosRoleAssignments.bicep' = if (!empty(userObjectId)) {
  name: 'cosmosRbacDeploy'
  params: {
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    assignments: cosmosRbacAssignments
  }
}

output vnetId string = networking.outputs.vnetId
output vnetName string = networking.outputs.vnetName
output aksClusterId string = aks.outputs.aksClusterId
output aksClusterName string = aks.outputs.aksClusterName
output aksFqdn string = aks.outputs.aksFqdn
output aksOidcIssuerUrl string = aks.outputs.aksOidcIssuerUrl
output acrId string = acr.outputs.acrId
output acrName string = acr.outputs.acrName
output acrLoginServer string = acr.outputs.acrLoginServer
output storageAccountId string = storage.outputs.storageAccountId
output storageAccountName string = storage.outputs.storageAccountName
output cosmosAccountId string = cosmos.outputs.cosmosAccountId
output cosmosAccountName string = cosmos.outputs.cosmosAccountName
output baseNameDash string = baseNameDash
output baseNameNoDash string = baseNameNoDash
