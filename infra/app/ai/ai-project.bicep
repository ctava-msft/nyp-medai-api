@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('AI hub name')
param aiHubName string

@description('AI hub display name')
param aiHubFriendlyName string = aiHubName

@description('AI hub description')
param aiHubDescription string = 'AI Hub'

@description('AI Project name')
param aiProjectName string

@description('AI Project display name')
param aiProjectFriendlyName string = aiProjectName

@description('AI Project description')
param aiProjectDescription string = 'AI Project'

@description('Resource ID of the storage account')
param storageAccountId string

@description('Resource ID of the AI Services')
param aiServicesId string

@description('AI Services endpoint')
param aiServicesEndpoint string

@description('key vault name')
param keyVaultName string


module keyVault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: 'keyVault'
  scope: resourceGroup()
  params: {
    location: location
    name: keyVaultName
  }
}

// Create AI Hub
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiHubName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiHubFriendlyName
    description: aiHubDescription
    storageAccount: storageAccountId
    keyVault: keyVault.outputs.resourceId
  }
  kind: 'hub'

  resource aiServicesConnection 'connections@2024-04-01' = {
    name: '${aiHubName}-connection-AIServices'
    properties: {
      category: 'AIServices'
      target: aiServicesEndpoint
      authType: 'ApiKey'
      credentials: {
        key: listKeys(aiServicesId, '2023-10-01-preview').key1
      }
      metadata: {
        ApiType: 'Azure'
        ResourceId: aiServicesId
        Location: location
      }
    }
  }
}

// Create AI Project
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiProjectName
  location: location
  tags: union(tags, {
    ProjectConnectionString: '${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${aiProjectName}'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiProjectFriendlyName
    description: aiProjectDescription
    hubResourceId: aiHub.id
  }
  kind: 'project'
}

// Role assignments for AI Project to access AI Services
resource cognitiveServicesContributorRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
  scope: subscription()
}

resource cognitiveServicesContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesId, cognitiveServicesContributorRole.id, aiProject.id)
  properties: {
    principalId: aiProject.identity.principalId
    roleDefinitionId: cognitiveServicesContributorRole.id
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesOpenAIUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  scope: subscription()
}

resource cognitiveServicesOpenAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, cognitiveServicesOpenAIUserRole.id, aiServicesId)
  properties: {
    principalId: aiProject.identity.principalId
    roleDefinitionId: cognitiveServicesOpenAIUserRole.id
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  scope: subscription()
}

resource cognitiveServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, cognitiveServicesUserRole.id, aiServicesId)
  properties: {
    principalId: aiProject.identity.principalId
    roleDefinitionId: cognitiveServicesUserRole.id
    principalType: 'ServicePrincipal'
  }
}

output aiHubId string = aiHub.id
output aiProjectName string = aiProject.name
output aiProjectId string = aiProject.id
output projectConnectionString string = aiProject.tags.ProjectConnectionString

