// Main Bicep file for ADL Invoice Processing Automation
// Orchestrates all infrastructure components across environments

targetScope = 'resourceGroup'

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Base name for resources')
param baseName string = 'adl-invoice'

@description('App Service Plan SKU')
@allowed([
  'B1'  // Basic tier (dev)
  'P1V2'  // Premium V2 (staging/prod)
  'P2V2'  // Premium V2 larger (prod)
])
param appServicePlanSku string

@description('Document Intelligence SKU')
@allowed([
  'F0'  // Free tier (dev/testing)
  'S0'  // Standard tier (prod)
])
param documentIntelligenceSku string = 'S0'

@description('Service Bus SKU')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param serviceBusSku string = 'Standard'

// ============================================================================
// TEAMS INTEGRATION (Optional - Multiple Methods Supported)
// ============================================================================

@description('Teams integration type')
@allowed([
  'none'      // No Teams integration
  'webhook'   // Incoming Webhook (deprecated but works)
  'workflow'  // Power Automate Workflow (recommended)
  'graph'     // Microsoft Graph API with Teams App
])
param teamsIntegrationType string = 'none'

@description('Teams webhook URL (for webhook type)')
@secure()
param teamsWebhookUrl string = ''

@description('Teams workflow URL (for workflow type - Power Automate)')
@secure()
param teamsWorkflowUrl string = ''

@description('Teams App client ID (for graph type)')
param teamsAppClientId string = ''

@description('Teams App client secret (for graph type)')
@secure()
param teamsAppClientSecret string = ''

@description('Teams channel ID (for graph type)')
param teamsChannelId string = ''

@description('Tags to apply to all resources')
param tags object = {
  Environment: environment
  Project: 'Invoice Processing'
  ManagedBy: 'Bicep'
}

// ============================================================================
// VARIABLES
// ============================================================================

var resourceSuffix = '${baseName}-${environment}-${location}'
var appServicePlanName = 'asp-${resourceSuffix}'
var webAppName = 'app-${resourceSuffix}'
var documentIntelligenceName = 'di-${resourceSuffix}'
var serviceBusNamespaceName = 'sb-${resourceSuffix}'
var logAnalyticsName = 'log-${resourceSuffix}'
var appInsightsName = 'appi-${resourceSuffix}'

// ============================================================================
// MODULES
// ============================================================================

// Monitoring (deploy first - needed by other resources)
module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    tags: tags
  }
}

// App Service (FastAPI backend)
module appService './modules/app-service.bicep' = {
  name: 'app-service-deployment'
  params: {
    location: location
    appServicePlanName: appServicePlanName
    webAppName: webAppName
    appServicePlanSku: appServicePlanSku
    documentIntelligenceEndpoint: documentIntelligence.outputs.endpoint
    documentIntelligenceKey: documentIntelligence.outputs.key
    serviceBusConnectionString: serviceBus.outputs.connectionString
    teamsIntegrationType: teamsIntegrationType
    teamsWebhookUrl: teamsWebhookUrl
    teamsWorkflowUrl: teamsWorkflowUrl
    teamsAppClientId: teamsAppClientId
    teamsAppClientSecret: teamsAppClientSecret
    teamsChannelId: teamsChannelId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: tags
  }
}

// Document Intelligence
module documentIntelligence './modules/document-intelligence.bicep' = {
  name: 'document-intelligence-deployment'
  params: {
    location: location
    documentIntelligenceName: documentIntelligenceName
    sku: documentIntelligenceSku
    tags: tags
  }
}

// Service Bus
module serviceBus './modules/service-bus.bicep' = {
  name: 'service-bus-deployment'
  params: {
    location: location
    serviceBusNamespaceName: serviceBusNamespaceName
    sku: serviceBusSku
    tags: tags
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Web App URL')
output webAppUrl string = appService.outputs.webAppUrl

@description('Web App name for deployment')
output webAppName string = appService.outputs.webAppName

@description('Document Intelligence endpoint')
output documentIntelligenceEndpoint string = documentIntelligence.outputs.endpoint

@description('Service Bus namespace')
output serviceBusNamespace string = serviceBus.outputs.namespaceName

@description('Application Insights instrumentation key')
output appInsightsInstrumentationKey string = monitoring.outputs.appInsightsInstrumentationKey

@description('Resource group name')
output resourceGroupName string = resourceGroup().name

@description('Environment deployed')
output environment string = environment