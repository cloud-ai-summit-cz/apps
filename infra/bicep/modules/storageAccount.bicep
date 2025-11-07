@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string
@description('Base name with dash constructed in main.')
param baseNameDash string

@description('Azure location for the storage account.')
param location string

@description('Allow public network access (keep Enabled until Private Endpoints are introduced).')
param publicNetworkAccess string = 'Enabled'

@description('Optional: Subnet ID for private endpoint. If empty, no private endpoint is created.')
param privateEndpointSubnetId string = ''

@description('Optional: Private DNS Zone ID for Blob storage. Required if privateEndpointSubnetId is provided.')
param privateDnsZoneId string = ''

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${baseNameNoDash}'
  location: location
  sku: {
    name: 'Standard_ZRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: publicNetworkAccess
    supportsHttpsTrafficOnly: true
  }
  tags: {
    baseNameDash: baseNameDash // references param to avoid unused warning & useful for grouping
  }
}

// Blob service (parent for containers)
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: sa
  name: 'default'
}

// Container for toy avatars
resource avatarsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'avatars'
  properties: {
    publicAccess: 'None'
  }
}

// Container for trip gallery images
resource galleryContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'gallery'
  properties: {
    publicAccess: 'None'
  }
}

// Private Endpoint for Blob storage (optional)
resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  name: 'pep-${baseNameDash}-storage'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-${baseNameDash}-storage-connection'
        properties: {
          privateLinkServiceId: sa.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

// DNS Zone Group for Private Endpoint
resource storageDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  parent: storagePrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-blob-core-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

@description('Blob service default child scope useful for data-plane role assignments.')
output blobDataScope string = '${sa.id}/blobServices/default'
@description('Full storage account resource ID.')
output storageAccountId string = sa.id
@description('Storage account name used.')
output storageAccountName string = 'st${baseNameNoDash}'
@description('Primary blob endpoint (data-plane URI).')
output blobEndpoint string = sa.properties.primaryEndpoints.blob
