@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Cosmos DB account name')
param accountName string

@description('Database name')
param databaseName string

@description('Container name for medical records')
param containerName string

param dataContributorIdentityIds string[] = []

resource account 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [
      { name: 'EnableServerless' }
    ]
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    enableFreeTier: false
    disableLocalAuth: true // Use RBAC only
    publicNetworkAccess: 'Enabled'
    networkAclBypass: 'AzureServices'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/MEDCode'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
        compositeIndexes: [
          [
            {
              path: '/MEDCode'
              order: 'ascending'
            }
            {
              path: '/Slot'
              order: 'ascending'
            }
          ]
        ]
      }
      defaultTtl: -1 // Disable TTL by default
    }
  }
}

var CosmosDbDataContributor = '00000000-0000-0000-0000-000000000002'

resource assignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = [for identityId in dataContributorIdentityIds: {
  name: guid(CosmosDbDataContributor, identityId, account.id)  
  parent: account
  properties: {
    principalId: identityId
    roleDefinitionId: resourceId('Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions', accountName, CosmosDbDataContributor)
    scope: account.id
  }
}]

output accountName string = account.name
output databaseName string = database.name
output containerName string = container.name
output documentEndpoint string = account.properties.documentEndpoint
output resourceId string = account.id
