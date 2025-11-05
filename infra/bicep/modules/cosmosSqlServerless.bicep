@description('Base name without dash constructed in main (letters only).')
param baseNameNoDash string
@description('Base name with dash constructed in main (reserved for future or tagging).')
param baseNameDash string

@description('Azure location for all resources.')
param location string

@description('Public network access toggle (remain Enabled until Private Endpoint introduced).')
param publicNetworkAccess string = 'Enabled'
// Consistency level hardcoded to Session (can be changed later if needed)

var cosmosAccountName = 'cos${baseNameNoDash}'
// Database and container names must match what application expects in .env
var cosmosDatabaseName = 'toytripdb'
var cosmosToysContainerName = 'toys'
var cosmosTripsContainerName = 'trips'

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosAccountName
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
  name: cosmosDatabaseName
  properties: {
    resource: {
      id: cosmosDatabaseName
    }
    options: {}
  }
}

// Create container via control plane (SDK cannot create containers due to disableKeyBasedMetadataWriteAccess)
resource toysContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: db
  name: cosmosToysContainerName
  properties: {
    resource: {
      id: cosmosToysContainerName
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
  name: cosmosTripsContainerName
  properties: {
    resource: {
      id: cosmosTripsContainerName
      partitionKey: {
        paths: ['/trip_id']
        kind: 'Hash'
      }
    }
    options: {}
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
output cosmosAccountName string = cosmosAccountName
@description('Cosmos database name used.')
output cosmosDatabaseName string = cosmosDatabaseName
@description('Cosmos toys container name used.')
output cosmosToysContainerName string = cosmosToysContainerName
@description('Cosmos trips container name used.')
output cosmosTripsContainerName string = cosmosTripsContainerName
@description('Document endpoint URI for data-plane SDK access.')
output cosmosEndpoint string = account.properties.documentEndpoint
