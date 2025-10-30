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
var cosmosDatabaseName = 'db${baseNameNoDash}'
var cosmosContainerName = 'c${baseNameNoDash}'

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

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: db
  name: cosmosContainerName
  properties: {
    resource: {
      id: cosmosContainerName
      partitionKey: {
        paths: ['/pk']
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
@description('Cosmos account name used.')
output cosmosAccountName string = cosmosAccountName
@description('Cosmos database name used.')
output cosmosDatabaseName string = cosmosDatabaseName
@description('Cosmos container name used.')
output cosmosContainerName string = cosmosContainerName
@description('Document endpoint URI for data-plane SDK access.')
output cosmosEndpoint string = account.properties.documentEndpoint
