@description('Array of RBAC assignments: { principalId: string, principalType: string, roleDefinitionId: string }')
param assignments array

// Resource group-scoped role assignments (this module is deployed at RG scope)
resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (assignment, i) in assignments: {
  name: guid(resourceGroup().id, assignment.principalId, assignment.roleDefinitionId, string(i))
  properties: {
    roleDefinitionId: assignment.roleDefinitionId
    principalId: assignment.principalId
    principalType: assignment.principalType
  }
}]
