@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string
@description('Base name with dash constructed in main.')
param baseNameDash string

@description('Azure location for all resources.')
param location string

@description('Public network access toggle.')
param publicNetworkAccess string = 'Enabled'

@description('Optional: Subnet ID for private endpoint. If empty, no private endpoint is created.')
param privateEndpointSubnetId string = ''

@description('Optional: Private DNS Zone ID for Service Bus. Required if privateEndpointSubnetId is provided.')
param privateDnsZoneId string = ''

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: 'sb-${baseNameDash}'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: true  // Enforce Managed Identity authentication only
  }
}

// Create addon-fulfill queue
resource addonFulfillQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'addon-fulfill'
  properties: {
    maxDeliveryCount: 3
    lockDuration: 'PT5M'  // 5 minutes
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    deadLetteringOnMessageExpiration: true
    enablePartitioning: false
  }
}

// Private Endpoint for Service Bus (optional)
resource serviceBusPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  name: 'pep-${baseNameDash}-servicebus'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-${baseNameDash}-servicebus-connection'
        properties: {
          privateLinkServiceId: serviceBusNamespace.id
          groupIds: ['namespace']
        }
      }
    ]
  }
}

// DNS Zone Group for Private Endpoint
resource serviceBusDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  parent: serviceBusPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-servicebus-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

@description('Service Bus namespace resource ID.')
output serviceBusNamespaceId string = serviceBusNamespace.id
@description('Service Bus namespace name.')
output serviceBusNamespaceName string = serviceBusNamespace.name
@description('Service Bus namespace fully qualified domain name.')
output serviceBusEndpoint string = '${serviceBusNamespace.name}.servicebus.windows.net'
@description('Addon fulfill queue name.')
output addonFulfillQueueName string = addonFulfillQueue.name
