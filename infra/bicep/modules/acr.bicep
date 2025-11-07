@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string

@description('Base name with dash constructed in main.')
param baseNameDash string

@description('Location for the Azure Container Registry.')
param location string

@description('SKU for Azure Container Registry.')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Standard'

@description('Enable public network access.')
param publicNetworkAccess string = 'Enabled'

@description('Optional: Subnet ID for private endpoint. If empty, no private endpoint is created.')
param privateEndpointSubnetId string = ''

@description('Optional: Private DNS Zone ID for ACR. Required if privateEndpointSubnetId is provided.')
param privateDnsZoneId string = ''

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${baseNameNoDash}'
  location: location
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: publicNetworkAccess
    networkRuleBypassOptions: 'AzureServices'
  }
}

// Private Endpoint for ACR (optional)
resource acrPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  name: 'pep-${baseNameNoDash}-acr'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-${baseNameDash}-acr-connection'
        properties: {
          privateLinkServiceId: acr.id
          groupIds: ['registry']
        }
      }
    ]
  }
}

// DNS Zone Group for Private Endpoint
resource acrDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  parent: acrPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-azurecr-io'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

output acrId string = acr.id
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
