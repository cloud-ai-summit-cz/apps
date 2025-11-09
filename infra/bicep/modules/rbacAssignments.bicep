@description('Array of RBAC assignments: { principalId: string, principalType: string, roleDefinitionId: string }')
param assignments array

// Resource group-scoped role assignments (this module is deployed at RG scope)
resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (assignment, index) in assignments: {
  // Include index in GUID to prevent collisions when same principal+role appears twice
  name: guid(resourceGroup().id, assignment.principalId, assignment.roleDefinitionId, string(index))
  properties: {
    roleDefinitionId: assignment.roleDefinitionId
    principalId: assignment.principalId
    principalType: assignment.principalType
  }
}]

@description('Count of role assignments processed.')
output count int = length(assignments)
