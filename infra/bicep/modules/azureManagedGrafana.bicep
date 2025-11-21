@description('Base name without dash for resource naming.')
param baseName string

@description('Location for Grafana workspace.')
param location string

@description('Azure Monitor workspace resource IDs to integrate with.')
param azureMonitorWorkspaceIds array = []

resource grafana 'Microsoft.Dashboard/grafana@2023-09-01' = {
  name: 'grafana-${baseName}'
  location: location
  sku: {
    name: 'Standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    grafanaIntegrations: {
      azureMonitorWorkspaceIntegrations: [
        for workspaceId in azureMonitorWorkspaceIds: {
          azureMonitorWorkspaceResourceId: workspaceId
        }
      ]
    }
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
    apiKey: 'Enabled'
    deterministicOutboundIP: 'Disabled'
    grafanaMajorVersion: '11'
  }
}

output grafanaId string = grafana.id
output grafanaName string = grafana.name
output grafanaEndpoint string = grafana.properties.endpoint
output grafanaPrincipalId string = grafana.identity.principalId
