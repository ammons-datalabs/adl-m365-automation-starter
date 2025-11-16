// Production environment parameters
// Production-grade configuration with appropriate SKUs

using '../main.bicep'

param environment = 'prod'
param location = 'westus3'  // West Coast deployment
param appServicePlanSku = 'P1V2'  // Premium for production workloads
param documentIntelligenceSku = 'S0'  // Standard tier
param serviceBusSku = 'Standard'  // Or 'Premium' for high availability

// Teams integration: configure for production notifications
param teamsIntegrationType = 'workflow'  // Recommended: Power Automate Workflow
// param teamsWorkflowUrl = ''  // Set workflow URL (stored in Key Vault recommended)

// Alternative: Use webhook (deprecated but works)
// param teamsIntegrationType = 'webhook'
// param teamsWebhookUrl = ''

// Alternative: Use Graph API (most control)
// param teamsIntegrationType = 'graph'
// param teamsAppClientId = ''
// param teamsAppClientSecret = ''  // Use Key Vault reference
// param teamsChannelId = ''