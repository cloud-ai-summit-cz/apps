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

// Grant AcrPull to kubelet identity
resource acrPullRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(resourceGroup().id, aksKubeletIdentity.id, acrPullRoleDefinition.id)
  properties: {
    roleDefinitionId: acrPullRoleDefinition.id
    principalId: aksKubeletIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Managed Identity Operator to cluster identity on kubelet identity
resource managedIdentityOperatorRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'f1a07417-d97a-45cb-824c-7a7467783830' // Managed Identity Operator
}

resource managedIdentityOperatorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aksKubeletIdentity
  name: guid(aksKubeletIdentity.id, aksClusterIdentity.id, managedIdentityOperatorRoleDefinition.id)
  properties: {
    roleDefinitionId: managedIdentityOperatorRoleDefinition.id
    principalId: aksClusterIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Network Contributor to cluster identity on resource group (for VNet access)
resource networkContributorRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '4d97b98b-1d4f-4787-a291-c67834d212e7' // Network Contributor
}

resource networkContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(resourceGroup().id, aksClusterIdentity.id, networkContributorRoleDefinition.id, 'network')
  properties: {
    roleDefinitionId: networkContributorRoleDefinition.id
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
    acrPullAssignment
    managedIdentityOperatorAssignment
    networkContributorAssignment
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

// Storage RBAC assignments (standard Azure RBAC via Microsoft.Authorization)
var storageRbacAssignments = [
  {
    principalObjectId: userObjectId
    roleName: 'Storage Blob Data Contributor'
    storageAccountName: storage.outputs.storageAccountName
  }
]

module storageRbac 'modules/roleAssignments.bicep' = if (!empty(userObjectId)) {
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

module cosmosRbac 'modules/cosmosRoleAssignments.bicep' = if (!empty(userObjectId)) {
  name: 'cosmosRbacDeploy'
  params: {
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    assignments: cosmosRbacAssignments
  }
}

// AKS RBAC Cluster Admin role assignment for user
resource aksClusterAdminRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b' // Azure Kubernetes Service RBAC Cluster Admin
}

resource aksUserClusterAdminAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userObjectId)) {
  scope: resourceGroup()
  name: guid(resourceGroup().id, userObjectId, aksClusterAdminRoleDefinition.id, 'aks-user-cluster-admin')
  properties: {
    roleDefinitionId: aksClusterAdminRoleDefinition.id
    principalId: userObjectId
    principalType: 'User'
  }
}

// AKS RBAC Cluster Admin role assignment for GitHub Workflow identity
resource aksWorkflowClusterAdminAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(gitHubWorkflowIdentityObjectId)) {
  scope: resourceGroup()
  name: guid(resourceGroup().id, gitHubWorkflowIdentityObjectId, aksClusterAdminRoleDefinition.id, 'aks-workflow-cluster-admin')
  properties: {
    roleDefinitionId: aksClusterAdminRoleDefinition.id
    principalId: gitHubWorkflowIdentityObjectId
    principalType: 'ServicePrincipal'
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
