// Staging environment parameters
// Production-like configuration for pre-production testing

using '../main.bicep'

param environment = 'staging'
param location = 'westus3'  // West Coast deployment
param appServicePlanSku = 'P1V2'  // Premium for production-like testing
param documentIntelligenceSku = 'S0'  // Standard tier
param serviceBusSku = 'Standard'

// Teams integration: configure based on your setup
param teamsIntegrationType = 'none'  // Change to 'webhook', 'workflow', or 'graph'
// param teamsWebhookUrl = ''  // Set if using webhook
// param teamsWorkflowUrl = ''  // Set if using Power Automate Workflow (recommended)
// param teamsAppClientId = ''  // Set if using Graph API
// param teamsAppClientSecret = ''  // Set if using Graph API
// param teamsChannelId = ''  // Set if using Graph API