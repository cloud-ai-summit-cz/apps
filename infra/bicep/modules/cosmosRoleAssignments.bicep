@description('Name of the Cosmos DB account for which to assign roles.')
param cosmosAccountName string

@description('Array of Cosmos data-plane role assignment objects: { principalObjectId: string, roleDefinitionId?: string, scope?: string }')
param assignments array

@description('Built-in Cosmos DB data-plane role definition IDs.')
var builtInRoles = {
  'Cosmos DB Built-in Data Reader': '00000000-0000-0000-0000-000000000001'
  'Cosmos DB Built-in Data Contributor': '00000000-0000-0000-0000-000000000002'
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

// Cosmos DB data-plane RBAC uses Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments
resource cosmosRoleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = [for assignment in assignments: {
  name: guid(cosmosAccount.id, assignment.principalObjectId, (assignment.?roleDefinitionId ?? builtInRoles[assignment.roleName]))
  parent: cosmosAccount
  properties: {
    principalId: assignment.principalObjectId
    // Role definition ID must be fully qualified resource ID for Cosmos
    roleDefinitionId: assignment.?roleDefinitionId ?? '${cosmosAccount.id}/sqlRoleDefinitions/${builtInRoles[assignment.roleName]}'
    // Scope can be account (default), database, or container level
    scope: assignment.?scope ?? cosmosAccount.id
  }
}]

@description('Count of Cosmos role assignments processed.')
output count int = length(assignments)
