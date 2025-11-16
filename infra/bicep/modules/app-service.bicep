// App Service module: Linux Web App for FastAPI
// Hosts the invoice processing API

@description('Azure region for resources')
param location string

@description('App Service Plan name')
param appServicePlanName string

@description('Web App name')
param webAppName string

@description('App Service Plan SKU')
@allowed([
  'B1'
  'P1V2'
  'P2V2'
])
param appServicePlanSku string

@description('Document Intelligence endpoint')
param documentIntelligenceEndpoint string

@description('Document Intelligence API key')
@secure()
param documentIntelligenceKey string

@description('Service Bus connection string')
@secure()
param serviceBusConnectionString string

// ============================================================================
// TEAMS INTEGRATION (Optional - Multiple Methods)
// ============================================================================

@description('Teams integration type')
@allowed([
  'none'
  'webhook'
  'workflow'
  'graph'
])
param teamsIntegrationType string

@description('Teams webhook URL (for webhook type)')
@secure()
param teamsWebhookUrl string

@description('Teams workflow URL (for workflow type)')
@secure()
param teamsWorkflowUrl string

@description('Teams App client ID (for graph type)')
param teamsAppClientId string

@description('Teams App client secret (for graph type)')
@secure()
param teamsAppClientSecret string

@description('Teams channel ID (for graph type)')
param teamsChannelId string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Tags to apply to resources')
param tags object

// ============================================================================
// APP SERVICE PLAN
// ============================================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: appServicePlanSku
  }
  kind: 'linux'
  properties: {
    reserved: true  // Required for Linux
  }
}

// ============================================================================
// WEB APP
// ============================================================================

resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: location
  tags: tags
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appCommandLine: 'python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000'
      appSettings: union([
        // Core Azure services
        {
          name: 'AZ_DI_ENDPOINT'
          value: documentIntelligenceEndpoint
        }
        {
          name: 'AZ_DI_API_KEY'
          value: documentIntelligenceKey
        }
        {
          name: 'SERVICE_BUS_CONNECTION_STRING'
          value: serviceBusConnectionString
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        // Application configuration
        {
          name: 'APPROVAL_AMOUNT_THRESHOLD'
          value: '500.0'
        }
        {
          name: 'APPROVAL_MIN_CONFIDENCE'
          value: '0.85'
        }
        {
          name: 'PYTHONUNBUFFERED'
          value: '1'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        // Teams integration type
        {
          name: 'TEAMS_INTEGRATION_TYPE'
          value: teamsIntegrationType
        }
      ],
      // Conditional Teams settings based on integration type
      teamsIntegrationType == 'webhook' ? [
        {
          name: 'TEAMS_WEBHOOK_URL'
          value: teamsWebhookUrl
        }
      ] : [],
      teamsIntegrationType == 'workflow' ? [
        {
          name: 'TEAMS_WORKFLOW_URL'
          value: teamsWorkflowUrl
        }
      ] : [],
      teamsIntegrationType == 'graph' ? [
        {
          name: 'TEAMS_APP_CLIENT_ID'
          value: teamsAppClientId
        }
        {
          name: 'TEAMS_APP_CLIENT_SECRET'
          value: teamsAppClientSecret
        }
        {
          name: 'TEAMS_CHANNEL_ID'
          value: teamsChannelId
        }
      ] : []
      )
    }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Web App URL')
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'

@description('Web App name')
output webAppName string = webApp.name

@description('Web App resource ID')
output webAppId string = webApp.id