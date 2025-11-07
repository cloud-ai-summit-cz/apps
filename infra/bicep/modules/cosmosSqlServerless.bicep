@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string
@description('Base name with dash constructed in main.')
param baseNameDash string

@description('Azure location for all resources.')
param location string

@description('Public network access toggle (remain Enabled until Private Endpoint introduced).')
param publicNetworkAccess string = 'Enabled'

@description('Optional: Subnet ID for private endpoint. If empty, no private endpoint is created.')
param privateEndpointSubnetId string = ''

@description('Optional: Private DNS Zone ID for Cosmos DB. Required if privateEndpointSubnetId is provided.')
param privateDnsZoneId string = ''

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: 'cosmos${baseNameNoDash}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableKeyBasedMetadataWriteAccess: true
    publicNetworkAccess: publicNetworkAccess
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

// Create database via control plane (SDK cannot create DB due to disableKeyBasedMetadataWriteAccess)
resource db 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: account
  name: 'toytripdb'
  properties: {
    resource: {
      id: 'toytripdb'
    }
    options: {}
  }
}

// Create container via control plane (SDK cannot create containers due to disableKeyBasedMetadataWriteAccess)
resource toysContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: db
  name: 'toys'
  properties: {
    resource: {
      id: 'toys'
      partitionKey: {
        paths: ['/toy_id']
        kind: 'Hash'
      }
    }
    options: {}
  }
}

// Create trips container
resource tripsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: db
  name: 'trips'
  properties: {
    resource: {
      id: 'trips'
      partitionKey: {
        paths: ['/trip_id']
        kind: 'Hash'
      }
    }
    options: {}
  }
}

// Private Endpoint for Cosmos DB (optional)
resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  name: 'pep-${baseNameDash}-cosmos'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-${baseNameDash}-cosmos-connection'
        properties: {
          privateLinkServiceId: account.id
          groupIds: ['Sql']
        }
      }
    ]
  }
}

// DNS Zone Group for Private Endpoint
resource cosmosDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneId)) {
  parent: cosmosPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-documents-azure-com'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

@description('Cosmos DB account resource ID.')
output cosmosAccountId string = account.id
@description('Cosmos SQL database resource ID.')
output cosmosDatabaseId string = db.id
@description('Cosmos toys container resource ID.')
output cosmosToysContainerId string = toysContainer.id
@description('Cosmos trips container resource ID.')
output cosmosTripsContainerId string = tripsContainer.id
@description('Cosmos account name used.')
output cosmosAccountName string = 'cosmos${baseNameNoDash}'
@description('Cosmos database name used.')
output cosmosDatabaseName string = 'toytripdb'
@description('Cosmos toys container name used.')
output cosmosToysContainerName string = 'toys'
@description('Cosmos trips container name used.')
output cosmosTripsContainerName string = 'trips'
@description('Document endpoint URI for data-plane SDK access.')
output cosmosEndpoint string = account.properties.documentEndpoint
