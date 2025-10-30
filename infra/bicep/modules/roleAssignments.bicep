@description('Array of storage role assignment objects: { principalObjectId: string, storageAccountName: string, roleName?: string, roleDefinitionId?: string }')
param assignments array

@description('Optional default principal type if not specified per assignment (User, ServicePrincipal, Group, etc.).')
param defaultPrincipalType string = 'User'

// Azure RBAC roles for Storage (control plane and data plane)
var roleMap = {
  'Storage Blob Data Contributor': subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  'Storage Blob Data Reader': subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
  'Storage Blob Data Owner': subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
}

// Reference existing storage accounts to get typed resource for scope
resource storageAccounts 'Microsoft.Storage/storageAccounts@2023-01-01' existing = [for assignment in assignments: {
  name: assignment.storageAccountName
}]

// Create role assignments deterministically so re-runs remain idempotent.
// Standard Azure RBAC for Storage accounts (uses Microsoft.Authorization/roleAssignments)
resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (assignment, i) in assignments: {
  name: guid(storageAccounts[i].id, assignment.principalObjectId, (assignment.?roleDefinitionId ?? roleMap[assignment.roleName]))
  scope: storageAccounts[i]
  properties: {
    roleDefinitionId: (assignment.?roleDefinitionId ?? roleMap[assignment.roleName])
    principalId: assignment.principalObjectId
    principalType: defaultPrincipalType
  }
}]

@description('Count of role assignments processed.')
output count int = length(assignments)
