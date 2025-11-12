@description('Base name with dash constructed in main.')
param baseNameDash string

@description('Location for all resources.')
param location string

@description('Virtual network address space.')
param vnetAddressPrefix string = '10.240.0.0/16'

@description('AKS nodes subnet address prefix.')
param aksNodesSubnetPrefix string = '10.240.0.0/22'

@description('AKS API server subnet address prefix.')
param aksApiSubnetPrefix string = '10.240.4.0/28'

@description('Private endpoints subnet address prefix.')
param privateEndpointsSubnetPrefix string = '10.240.5.0/24'

// Public IP address for NAT Gateway (Zone-redundant Standard SKU)
resource natPublicIp 'Microsoft.Network/publicIPAddresses@2024-01-01' = {
  name: 'pip-${baseNameDash}-natgw'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  zones: ['1', '2', '3']
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    idleTimeoutInMinutes: 4
  }
}

// Public IP address for NGINX Ingress Controller - Standard SKU with DNS label
resource ingressPublicIp 'Microsoft.Network/publicIPAddresses@2024-01-01' = {
  name: 'pip-${baseNameDash}-ingress'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  zones: ['1', '2', '3']
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    idleTimeoutInMinutes: 4
    dnsSettings: {
      domainNameLabel: baseNameDash
    }
  }
}

// NAT Gateway 
resource natGateway 'Microsoft.Network/natGateways@2024-01-01' = {
  name: 'ng-${baseNameDash}'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: 4
    publicIpAddresses: [
      { id: natPublicIp.id }
    ]
  }
}

// Network Security Group for AKS nodes subnet
resource aksNodesNsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${baseNameDash}-aks-nodes'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          description: 'Allow Azure Load Balancer health probes - required for ingress controller'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHttpInbound'
        properties: {
          description: 'Allow HTTP traffic from Internet'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHttpsInbound'
        properties: {
          description: 'Allow HTTPS traffic from Internet'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 120
          direction: 'Inbound'
        }
      }
    ]
  }
}

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: 'vnet-${baseNameDash}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: [
      {
        name: 'snet-aks-nodes'
        properties: {
          addressPrefix: aksNodesSubnetPrefix
          natGateway: {
            id: natGateway.id
          }
          networkSecurityGroup: {
            id: aksNodesNsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'snet-aks-api'
        properties: {
          addressPrefix: aksApiSubnetPrefix
          delegations: [
            {
              name: 'aks-delegation'
              properties: {
                serviceName: 'Microsoft.ContainerService/managedClusters'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointsSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

// Private DNS Zones for Azure services
resource cosmosDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource blobDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
}

resource acrDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurecr.io'
  location: 'global'
}

// Link DNS zones to VNet
resource cosmosVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: cosmosDnsZone
  name: 'vnet-${baseNameDash}-cosmos-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

resource blobVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: blobDnsZone
  name: 'vnet-${baseNameDash}-blob-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

resource acrVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: acrDnsZone
  name: 'vnet-${baseNameDash}-acr-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

// Outputs
output vnetId string = vnet.id
output vnetName string = vnet.name

output aksNodesSubnetId string = '${vnet.id}/subnets/snet-aks-nodes'
output aksApiSubnetId string = '${vnet.id}/subnets/snet-aks-api'
output privateEndpointsSubnetId string = '${vnet.id}/subnets/snet-private-endpoints'

output cosmosDnsZoneId string = cosmosDnsZone.id
output blobDnsZoneId string = blobDnsZone.id
output acrDnsZoneId string = acrDnsZone.id

output natGatewayId string = natGateway.id

output ingressPublicIpName string = ingressPublicIp.name
output ingressPublicIpAddress string = ingressPublicIp.properties.ipAddress
output ingressPublicIpFqdn string = ingressPublicIp.properties.dnsSettings.fqdn
output ingressPublicIpResourceGroup string = resourceGroup().name
