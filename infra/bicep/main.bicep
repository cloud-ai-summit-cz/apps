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

@description('Logical workloads that require their own managed identities (expand as needed).')
var workloadIdentities = [
  {
    name: 'toy'
    serviceAccountNamespace: 'toytrip-staging'
    serviceAccountName: 'toy-service'
  }
  {
    name: 'trip'
    serviceAccountNamespace: 'toytrip-staging'
    serviceAccountName: 'trip-service'
  }
]

// Deterministic unique suffix seeded by subscription + prefix (6 characters)
var rawUnique = uniqueString(subscription().id, prefix)
// Replace digits with letters a-j to satisfy "letters only" requirement, then take first 6 chars
var sanitizedUnique = substring(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(rawUnique, '0', 'a'), '1', 'b'), '2', 'c'), '3', 'd'), '4', 'e'), '5', 'f'), '6', 'g'), '7', 'h'), '8', 'i'), '9', 'j'), 0, 6)
var baseNameDash = '${prefix}-${sanitizedUnique}'
var baseNameNoDash = '${prefix}${sanitizedUnique}'
var workloadIdentitySpecs = [for (identity, idx) in workloadIdentities: {
  idx: idx
  name: toLower(identity.name)
  serviceAccountNamespace: identity.serviceAccountNamespace
  serviceAccountName: identity.serviceAccountName
  identityName: 'id-${baseNameDash}-${toLower(identity.name)}'
  federatedCredentialName: 'fic-${toLower(identity.name)}'
  federatedSubject: 'system:serviceaccount:${identity.serviceAccountNamespace}:${identity.serviceAccountName}'
}]

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

resource workloadUserAssignedIdentities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [
  for identity in workloadIdentitySpecs: {
    name: identity.identityName
    location: location
  }
]

resource workloadFederatedCredentials 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = [
  for identity in workloadIdentitySpecs: {
    parent: workloadUserAssignedIdentities[identity.idx]
    name: identity.federatedCredentialName
    properties: {
      issuer: aks.outputs.aksOidcIssuerUrl
      subject: identity.federatedSubject
      audiences: [
        'api://AzureADTokenExchange'
      ]
    }
  }
]


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

var cosmosAccountName = 'cosmos${baseNameNoDash}'
var cosmosAccountId = resourceId('Microsoft.DocumentDB/databaseAccounts', cosmosAccountName)

var cosmosBuiltInRoles = {
  'Cosmos DB Built-in Data Reader': '00000000-0000-0000-0000-000000000001'
  'Cosmos DB Built-in Data Contributor': '00000000-0000-0000-0000-000000000002'
}

resource cosmosAccountExisting 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: cosmosAccountName
}


// =============================================================================
// RBAC Assignments
// =============================================================================

var sameIdentity = !empty(userObjectId) && !empty(gitHubWorkflowIdentityObjectId) && userObjectId == gitHubWorkflowIdentityObjectId

resource aksKubeletAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, 'aksKubeletAcrPull')
  properties: {
    roleDefinitionId: roleDefinitions.AcrPull
    principalId: aksKubeletIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksClusterNetworkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, 'aksClusterNetworkContributor')
  properties: {
    roleDefinitionId: roleDefinitions.NetworkContributor
    principalId: aksClusterIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource userStorageBlobAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userObjectId)) {
  name: guid(resourceGroup().id, 'userStorageBlobAssignment')
  properties: {
    roleDefinitionId: roleDefinitions.StorageBlobDataContributor
    principalId: userObjectId
    principalType: 'User'
  }
}

resource userAksAdminAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userObjectId)) {
  name: guid(resourceGroup().id, 'userAksAdminAssignment')
  properties: {
    roleDefinitionId: roleDefinitions.AksRbacClusterAdmin
    principalId: userObjectId
    principalType: 'User'
  }
}

resource workflowAksAdminAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(gitHubWorkflowIdentityObjectId) && !sameIdentity) {
  name: guid(resourceGroup().id, 'workflowAksAdminAssignment')
  properties: {
    roleDefinitionId: roleDefinitions.AksRbacClusterAdmin
    principalId: gitHubWorkflowIdentityObjectId
    principalType: 'ServicePrincipal'
  }
}

resource workloadStorageAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for identity in workloadIdentitySpecs: {
    name: guid(resourceGroup().id, 'workloadStorage', identity.identityName)
    properties: {
      roleDefinitionId: roleDefinitions.StorageBlobDataContributor
      principalId: workloadUserAssignedIdentities[identity.idx].properties.principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// =============================================================================
// Cosmos DB RBAC (separate - uses different API)
// =============================================================================

var userCosmosAssignments = !empty(userObjectId) ? [
  {
    principalObjectId: userObjectId
    roleName: 'Cosmos DB Built-in Data Contributor'
  }
] : []

resource cosmosUserRoleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = [
  for (assignment, idx) in userCosmosAssignments: {
    name: guid(cosmosAccountId, 'user', string(idx))
    parent: cosmosAccountExisting
    properties: {
      principalId: assignment.principalObjectId
      roleDefinitionId: assignment.?roleDefinitionId ?? '${cosmosAccountId}/sqlRoleDefinitions/${cosmosBuiltInRoles[assignment.roleName]}'
      scope: assignment.?scope ?? cosmosAccountId
    }
  }
]

resource cosmosWorkloadRoleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = [
  for identity in workloadIdentitySpecs: {
    name: guid(cosmosAccountId, 'workload', identity.identityName)
    parent: cosmosAccountExisting
    properties: {
      principalId: workloadUserAssignedIdentities[identity.idx].properties.principalId
      roleDefinitionId: '${cosmosAccountId}/sqlRoleDefinitions/${cosmosBuiltInRoles['Cosmos DB Built-in Data Contributor']}'
      scope: cosmosAccountId
    }
  }
]

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
output workloadIdentities array = [
  for identity in workloadIdentitySpecs: {
    name: identity.name
    resourceId: workloadUserAssignedIdentities[identity.idx].id
    clientId: workloadUserAssignedIdentities[identity.idx].properties.clientId
    principalId: workloadUserAssignedIdentities[identity.idx].properties.principalId
    serviceAccountNamespace: identity.serviceAccountNamespace
    serviceAccountName: identity.serviceAccountName
    federatedSubject: identity.federatedSubject
  }
]
output baseNameDash string = baseNameDash
output baseNameNoDash string = baseNameNoDash
// Ingress public IP details for platform configuration
output ingressPublicIpName string = networking.outputs.ingressPublicIpName
output ingressPublicIpAddress string = networking.outputs.ingressPublicIpAddress
output ingressPublicIpFqdn string = networking.outputs.ingressPublicIpFqdn
output ingressPublicIpResourceGroup string = resourceGroup().name
