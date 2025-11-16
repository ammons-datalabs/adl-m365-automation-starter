// Development environment parameters
// Cost-optimized with free/basic tiers where possible

using '../main.bicep'

param environment = 'dev'
param location = 'westus3'  // West Coast deployment
param appServicePlanSku = 'B1'  // Basic tier for cost savings
param documentIntelligenceSku = 'F0'  // Free tier for development
param serviceBusSku = 'Basic'

// Teams integration: none by default (add manually if needed)
param teamsIntegrationType = 'none'
// param teamsWebhookUrl = ''  // Uncomment and set if using webhook
// param teamsWorkflowUrl = ''  // Uncomment and set if using workflow