param principalId string
param roleDefinitionId string
param cognitiveServicesName string

resource cognitiveServices 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' existing = {
  name: cognitiveServicesName
}

// Allow access from API to Cognitive Services using a managed identity
resource cognitiveServicesRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(cognitiveServices.id, principalId, roleDefinitionId)
  scope: cognitiveServices
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output ROLE_ASSIGNMENT_NAME string = cognitiveServicesRoleAssignment.name
