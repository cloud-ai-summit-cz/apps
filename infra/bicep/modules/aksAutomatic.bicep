@description('Base name for resource naming.')
param baseName string

@description('Location for the AKS cluster.')
param location string

@description('Subnet ID for AKS cluster nodes.')
param clusterSubnetId string

@description('Subnet ID for AKS API server VNET integration.')
param apiServerSubnetId string

@description('User-assigned managed identity resource ID for the cluster.')
param clusterIdentityId string

@description('User-assigned managed identity principal ID for the cluster.')
param clusterIdentityPrincipalId string

@description('User-assigned managed identity resource ID for kubelet (AcrPull).')
param kubeletIdentityId string

@description('User-assigned managed identity principal ID for kubelet.')
param kubeletIdentityPrincipalId string

// AKS Automatic cluster with custom VNet
resource aks 'Microsoft.ContainerService/managedClusters@2024-09-02-preview' = {
  name: 'aks-${baseName}'
  location: location
  sku: {
    name: 'Automatic'
    tier: 'Standard'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${clusterIdentityId}': {}
    }
  }
  properties: {
    // AKS Automatic - node provisioning handled automatically (no enableAutoScaling needed)
    agentPoolProfiles: [
      {
        name: 'systempool'
        mode: 'System'
        count: 3 // Initial count
        vnetSubnetID: clusterSubnetId
      }
    ]
    // API Server with VNET integration (public endpoint + private network)
    apiServerAccessProfile: {
      subnetId: apiServerSubnetId
      enablePrivateCluster: false // Public endpoint with VNET integration
    }
    // Network profile with Azure CNI Overlay and Cilium
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkPolicy: 'cilium'
      networkDataplane: 'cilium'
      loadBalancerSku: 'standard'
      outboundType: 'userAssignedNATGateway' // Uses our NAT Gateway
      serviceCidr: '10.250.0.0/16'
      dnsServiceIP: '10.250.0.10'
      // Advanced Container Networking Services (observability)
      advancedNetworking: {
        enabled: true
        observability: {
          enabled: true
        }
      }
    }
    // Kubelet identity for ACR pull
    identityProfile: {
      kubeletidentity: {
        resourceId: kubeletIdentityId
        clientId: reference(kubeletIdentityId, '2023-01-31').clientId
        objectId: kubeletIdentityPrincipalId
      }
    }
    // Azure RBAC for Kubernetes authorization
    aadProfile: {
      managed: true
      enableAzureRBAC: true
    }
    // Disable local accounts (use Azure AD only)
    disableLocalAccounts: true
    // Security and operational features
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
      imageCleaner: {
        enabled: true
        intervalHours: 168 // 7 days - recommended value for AKS Automatic
      }
    }
    oidcIssuerProfile: {
      enabled: true
    }
    // Automatic upgrades
    autoUpgradeProfile: {
      upgradeChannel: 'stable'
      nodeOSUpgradeChannel: 'NodeImage'
    }
    // Monitoring with Managed Prometheus and Container Insights
    azureMonitorProfile: {
      metrics: {
        enabled: true
        kubeStateMetrics: {
          metricLabelsAllowlist: ''
          metricAnnotationsAllowList: ''
        }
      }
    }
  }
}

output aksClusterId string = aks.id
output aksClusterName string = aks.name
output aksFqdn string = aks.properties.fqdn
output aksOidcIssuerUrl string = aks.properties.oidcIssuerProfile.issuerURL
output aksKubeletIdentityObjectId string = aks.properties.identityProfile.kubeletidentity.objectId
