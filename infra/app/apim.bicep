@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('APIM service name')
param serviceName string

@description('Publisher email for APIM')
param publisherEmail string = 'admin@contoso.com'

@description('Publisher name for APIM')
param publisherName string = 'Medical Data API Publisher'

@description('Pricing tier of the APIM service')
@allowed(['Developer', 'Basic', 'Standard', 'Premium', 'Consumption'])
param sku string = 'Standard'

@description('The Azure Function App backend URL')
param functionAppUrl string

@description('User-assigned managed identity resource ID for APIM')
param userAssignedIdentityId string

resource apimService 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: serviceName
  location: location
  tags: tags
  sku: {
    name: sku
    capacity: sku == 'Consumption' ? 0 : 1
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    publicNetworkAccess: 'Enabled'
    virtualNetworkType: 'None'
    disableGateway: false
    developerPortalStatus: 'Enabled'
    customProperties: {
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Protocols.Server.Http2': 'true'
    }
  }
}

// API for Medical Data Text-to-SQL Service
resource medicalDataApi 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apimService
  name: 'medical-data-api'
  properties: {
    displayName: 'Medical Data Text-to-SQL API'
    description: 'API for converting natural language queries to SQL and executing them against medical data'
    serviceUrl: functionAppUrl
    path: 'medical'
    protocols: ['https']
    subscriptionRequired: true
    apiVersion: 'v1'
    apiVersionSetId: medicalDataApiVersionSet.id
    authenticationSettings: {
      oAuth2AuthenticationSettings: []
      openidAuthenticationSettings: []
    }
  }
}

resource medicalDataApiVersionSet 'Microsoft.ApiManagement/service/apiVersionSets@2023-05-01-preview' = {
  parent: apimService
  name: 'medical-data-api-version-set'
  properties: {
    displayName: 'Medical Data API'
    description: 'Version set for Medical Data Text-to-SQL API'
    versioningScheme: 'Segment'
  }
}

// Operations for the Medical Data API
resource textToSqlOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: medicalDataApi
  name: 'text-to-sql'
  properties: {
    displayName: 'Convert Natural Language to SQL'
    method: 'POST'
    urlTemplate: '/text-to-sql'
    description: 'Convert natural language queries to SQL and execute them against medical data'
    request: {
      queryParameters: []
      headers: []
      representations: [
        {
          contentType: 'application/json'
        }
      ]
    }
    responses: [
      {
        statusCode: 200
        description: 'Successful response'
        representations: [
          {
            contentType: 'application/json'
          }
        ]
      }
      {
        statusCode: 400
        description: 'Bad request'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

resource sampleDataOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: medicalDataApi
  name: 'sample-data'
  properties: {
    displayName: 'Get Sample Medical Data'
    method: 'GET'
    urlTemplate: '/sample-data'
    description: 'Retrieve sample medical data records from the database'
    request: {
      queryParameters: [
        {
          name: 'limit'
          type: 'integer'
          description: 'Maximum number of records to return (1-100, default: 10)'
          defaultValue: '10'
        }
      ]
      headers: []
    }
    responses: [
      {
        statusCode: 200
        description: 'Successful response with sample data'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

resource uploadDataOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: medicalDataApi
  name: 'upload-medical-data'
  properties: {
    displayName: 'Upload Medical Data'
    method: 'POST'
    urlTemplate: '/medical-data'
    description: 'Upload medical data records to the database'
    request: {
      queryParameters: []
      headers: []
      representations: [
        {
          contentType: 'application/json'
        }
      ]
    }
    responses: [
      {
        statusCode: 200
        description: 'Successful upload'
      }
      {
        statusCode: 400
        description: 'Bad request'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

resource healthCheckOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: medicalDataApi
  name: 'health-check'
  properties: {
    displayName: 'Health Check'
    method: 'GET'
    urlTemplate: '/health'
    description: 'Check the health status of the medical data service'
    responses: [
      {
        statusCode: 200
        description: 'Service is healthy'
      }
      {
        statusCode: 503
        description: 'Service is degraded or unhealthy'
      }
    ]
  }
}

// Products and subscriptions
resource medicalDataProduct 'Microsoft.ApiManagement/service/products@2023-05-01-preview' = {
  parent: apimService
  name: 'medical-data-product'
  properties: {
    displayName: 'Medical Data API Product'
    description: 'Product for accessing medical data text-to-SQL services'
    subscriptionRequired: true
    approvalRequired: true
    state: 'published'
    subscriptionsLimit: 100
    terms: 'By using this API, you agree to comply with all applicable healthcare data regulations and privacy requirements.'
  }
}

resource productApiLink 'Microsoft.ApiManagement/service/products/apis@2023-05-01-preview' = {
  parent: medicalDataProduct
  name: medicalDataApi.name
}

// Policies for rate limiting and security
resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: medicalDataApi
  name: 'policy'
  properties: {
    value: '''
      <policies>
        <inbound>
          <base />
          <rate-limit calls="100" renewal-period="60" />
          <rate-limit-by-key calls="10" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
          <cors allow-credentials="false">
            <allowed-origins>
              <origin>*</origin>
            </allowed-origins>
            <allowed-methods>
              <method>GET</method>
              <method>POST</method>
              <method>OPTIONS</method>
            </allowed-methods>
            <allowed-headers>
              <header>Content-Type</header>
              <header>Authorization</header>
            </allowed-headers>
          </cors>
          <set-header name="X-API-Version" exists-action="override">
            <value>v1</value>
          </set-header>
        </inbound>
        <backend>
          <base />
        </backend>
        <outbound>
          <base />
          <set-header name="X-Powered-By" exists-action="delete" />
          <set-header name="Server" exists-action="delete" />
        </outbound>
        <on-error>
          <base />
        </on-error>
      </policies>
    '''
  }
}

output serviceName string = apimService.name
output serviceUrl string = 'https://${apimService.properties.gatewayUrl}'
output portalUrl string = apimService.properties.portalUrl != null ? apimService.properties.portalUrl : ''
output managementApiUrl string = apimService.properties.managementApiUrl
output resourceId string = apimService.id
