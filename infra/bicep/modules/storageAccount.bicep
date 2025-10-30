@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string
@description('Base name with dash constructed in main (currently unused, reserved for future).')
param baseNameDash string

@description('Azure location for the storage account.')
param location string

@description('Allow public network access (keep Enabled until Private Endpoints are introduced).')
param publicNetworkAccess string = 'Enabled'

// SKU fixed to Standard_ZRS (zone-redundant); remove parameterization per request
// (Can be reintroduced later if flexibility needed.)

var storageAccountName = 'st${baseNameNoDash}'

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
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

@description('Blob service default child scope useful for data-plane role assignments.')
output blobDataScope string = '${sa.id}/blobServices/default'
@description('Full storage account resource ID.')
output storageAccountId string = sa.id
@description('Storage account name used.')
output storageAccountName string = storageAccountName
@description('Primary blob endpoint (data-plane URI).')
output blobEndpoint string = sa.properties.primaryEndpoints.blob
