@description('Base name with dash for resource naming.')
param baseNameDash string

@description('Location for all monitoring resources.')
param location string

@description('Log Analytics workspace retention in days (30-730).')
param retentionInDays int = 30

@description('Pricing tier for Log Analytics.')
param sku string = 'PerGB2018'

// =============================================================================
// Log Analytics Workspace for Container Insights
// =============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${baseNameDash}'
  location: location
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =============================================================================
// Application Insights
// =============================================================================
// DisableLocalAuth is set to true for security (blocks connection string auth).
// OTEL Collector uses azureauthextension (v0.123.0+) with workload identity
// to authenticate via AAD/Entra when sending telemetry.
// The otelcollector managed identity requires "Monitoring Metrics Publisher" role.

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${baseNameDash}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    DisableLocalAuth: true
  }
}

// =============================================================================
// Azure Monitor Workspace for Prometheus Metrics
// =============================================================================

resource azureMonitorWorkspace 'Microsoft.Monitor/accounts@2023-04-03' = {
  name: 'amw-${baseNameDash}'
  location: location
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

// Data Collection Endpoint for Prometheus metrics ingestion
resource dataCollectionEndpoint 'Microsoft.Insights/dataCollectionEndpoints@2023-03-11' = {
  name: 'dce-${baseNameDash}'
  location: location
  properties: {
    networkAcls: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Data Collection Rule for Prometheus metrics
resource dataCollectionRule 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: 'dcr-${baseNameDash}-prometheus'
  location: location
  kind: 'Linux'
  properties: {
    dataCollectionEndpointId: dataCollectionEndpoint.id
    dataSources: {
      prometheusForwarder: [
        {
          streams: [
            'Microsoft-PrometheusMetrics'
          ]
          labelIncludeFilter: {}
          name: 'PrometheusDataSource'
        }
      ]
    }
    destinations: {
      monitoringAccounts: [
        {
          accountResourceId: azureMonitorWorkspace.id
          name: 'MonitoringAccount'
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          'Microsoft-PrometheusMetrics'
        ]
        destinations: [
          'MonitoringAccount'
        ]
      }
    ]
  }
}

// =============================================================================
// Outputs
// =============================================================================

// Log Analytics Workspace outputs
output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
output logAnalyticsWorkspaceCustomerId string = logAnalytics.properties.customerId

// Application Insights outputs
output applicationInsightsId string = appInsights.id
output applicationInsightsName string = appInsights.name
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output applicationInsightsIngestionEndpoint string = 'https://${location}.in.applicationinsights.azure.com/'

// Azure Monitor Workspace outputs
output azureMonitorWorkspaceId string = azureMonitorWorkspace.id
output azureMonitorWorkspaceName string = azureMonitorWorkspace.name
output azureMonitorWorkspaceQueryEndpoint string = azureMonitorWorkspace.properties.metrics.prometheusQueryEndpoint
output azureMonitorWorkspaceIngestionEndpoint string = azureMonitorWorkspace.properties.metrics.internalId

// Data Collection Rule outputs
output dataCollectionRuleId string = dataCollectionRule.id
output dataCollectionRuleImmutableId string = dataCollectionRule.properties.immutableId
output dataCollectionRuleName string = dataCollectionRule.name
output dataCollectionEndpointId string = dataCollectionEndpoint.id
output dataCollectionEndpointIngestionEndpoint string = dataCollectionEndpoint.properties.metricsIngestion.endpoint
