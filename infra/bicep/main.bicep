
@description('Location for resources')
param location string = resourceGroup().location

@description('Base name for the Web App')
param baseName string

// NOTE: Minimal placeholder. Build out with App Service Plan, Web App, Key Vault, and App Insights.
// For Container Apps or Functions, replace with appropriate modules.

output notes string = 'This is a placeholder. Add App Service, Key Vault, and App Insights as needed.'
