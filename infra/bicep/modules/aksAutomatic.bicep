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

@description('Log Analytics workspace resource ID for Container Insights.')
param logAnalyticsWorkspaceId string = ''

@description('Data Collection Rule resource ID for Prometheus metrics.')
param dataCollectionRuleId string = ''

// AKS Automatic cluster with custom VNet
resource aks 'Microsoft.ContainerService/managedClusters@2025-06-02-preview' = {
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
    agentPoolProfiles: [
      {
        name: 'systempool'
        mode: 'System'
        count: 2
        vnetSubnetID: clusterSubnetId
      }
      {
        name: 'userpool'
        mode: 'User'
        count: 1
        vnetSubnetID: clusterSubnetId
      }
    ]
    // API Server with VNET integration (public endpoint + private network)
    apiServerAccessProfile: {
      subnetId: apiServerSubnetId
      enablePrivateCluster: false
    }
    // Network profile with Azure CNI Overlay and Cilium
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkPolicy: 'cilium'
      networkDataplane: 'cilium'
      loadBalancerSku: 'standard'
      outboundType: 'userAssignedNATGateway'
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
      defender: {
        logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceId
        securityMonitoring: {
          enabled: true
        }
      }
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
    addonProfiles: {
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspaceId
          useAADAuth: 'true'
        }
      }
    }
    serviceMeshProfile: {
      mode: 'Istio'
      istio: {
        components: {
          ingressGateways: [
            {
              enabled: true
              mode: 'External'
            }
          ]
        }
      }
    }
    ingressProfile: {
      gatewayAPI: {
        installation: 'Standard'
      }
      webAppRouting: {
        enabled: true
        dnsZoneResourceIds: []
      }
    }
  }
}

// Data Collection Rule Association for Prometheus metrics
resource dcra 'Microsoft.Insights/dataCollectionRuleAssociations@2022-06-01' = if (!empty(dataCollectionRuleId)) {
  name: 'dcra-${split(dataCollectionRuleId, '/')[8]}'
  scope: aks
  properties: {
    dataCollectionRuleId: dataCollectionRuleId
    description: 'Association of Prometheus Data Collection Rule with AKS cluster'
  }
}

resource aksSafeguardsPolicyAssignment 'Microsoft.Authorization/policyAssignments@2022-06-01' = {
  name: 'aks-deployment-safeguards-policy-assignment'
  scope: aks
  location: location
  properties: {
    displayName: 'AKS Deployment Safeguards Policy Assignment'
    description: 'Deployment safeguards should help guide developers towards AKS recommended best practices'
    policyDefinitionId: '/providers/Microsoft.Authorization/policySetDefinitions/c047ea8e-9c78-49b2-958b-37e56d291a44'
    parameters: {
      warn: {
        value: true
      }
      effect: {
        value: 'Audit'
      }
      effectForMutationPolicies: {
        value: 'Disabled'
      }
      allowedUsers: {
        value: [
          'nodeclient'
          'system:serviceaccount:kube-system:aci-connector-linux'
          'system:serviceaccount:kube-system:node-controller'
          'acsService'
          'aksService'
          'system:serviceaccount:kube-system:cloud-node-manager'
          'system:serviceaccount:kube-system:cilium-operator'
        ]
      }
      allowedGroups: {
        value: [
          'system:node'
          'system:serviceaccounts:kube-system'
        ]
      }
      cpuLimit: {
        value: '5'
      }
      memoryLimit: {
        value: '5Gi'
      }
      labels: {
        value: [
          'kubernetes.azure.com'
        ]
      }
      allowedContainerImagesRegex: {
        value: '.*'
      }
      reservedTaints: {
        value: [
          'CriticalAddonsOnly'
        ]
      }
    }
  }
}

output aksClusterId string = aks.id
output aksClusterName string = aks.name
output aksFqdn string = aks.properties.fqdn
output aksOidcIssuerUrl string = aks.properties.oidcIssuerProfile.issuerURL
output aksKubeletIdentityObjectId string = aks.properties.identityProfile.kubeletidentity.objectId
output clusterIdentityPrincipalId string = clusterIdentityPrincipalId
