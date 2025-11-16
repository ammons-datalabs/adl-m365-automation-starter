# Bicep Infrastructure as Code

This directory contains Bicep templates for deploying the ADL Invoice Processing infrastructure to Azure.

## Overview

The Bicep templates provision a complete invoice processing system including:
- **App Service**: Linux Web App hosting FastAPI backend
- **Document Intelligence**: Azure AI for invoice OCR and field extraction
- **Service Bus**: Event-driven messaging for invoice events
- **Monitoring**: Application Insights + Log Analytics

## Directory Structure

```
infra/bicep/
├── main.bicep                    # Main orchestration file
├── modules/                      # Reusable Bicep modules
│   ├── app-service.bicep        # Web App + App Service Plan
│   ├── document-intelligence.bicep
│   ├── service-bus.bicep        # Namespace + Queue
│   └── monitoring.bicep         # App Insights + Log Analytics
├── parameters/                  # Environment-specific parameters
│   ├── dev.bicepparam
│   ├── staging.bicepparam
│   └── prod.bicepparam
└── README.md                    # This file
```

## Prerequisites

- Azure CLI 2.50+ with Bicep support
- Azure subscription with permissions to create resources
- Resource group created (or will be created during deployment)

## Deployment

### 1. Create Resource Group

```bash
# Development
az group create --name rg-adl-invoice-dev --location westus3

# Staging
az group create --name rg-adl-invoice-staging --location westus3

# Production
az group create --name rg-adl-invoice-prod --location westus3
```

### 2. Deploy Infrastructure

**Development:**
```bash
az deployment group create \
  --resource-group rg-adl-invoice-dev \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

**Staging:**
```bash
az deployment group create \
  --resource-group rg-adl-invoice-staging \
  --template-file main.bicep \
  --parameters parameters/staging.bicepparam
```

**Production:**
```bash
az deployment group create \
  --resource-group rg-adl-invoice-prod \
  --template-file main.bicep \
  --parameters parameters/prod.bicepparam
```

### 3. What-If Analysis (Preview Changes)

Before deploying, see what will be created/modified:

```bash
az deployment group what-if \
  --resource-group rg-adl-invoice-dev \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

## Teams Integration Options

The infrastructure supports **multiple Teams notification methods**:

### Option 1: None (Default)
No Teams integration. Simplest option for initial setup.

```bicep
param teamsIntegrationType = 'none'
```

### Option 2: Webhook (Legacy - Deprecated)
Traditional incoming webhook. Still works but being phased out by Microsoft.

```bicep
param teamsIntegrationType = 'webhook'
param teamsWebhookUrl = 'https://outlook.office.com/webhook/...'
```

**Setup:**
1. In Teams channel → Connectors → Incoming Webhook
2. Copy the webhook URL
3. Pass as parameter or store in Key Vault

### Option 3: Workflow (Recommended)
Power Automate workflow with HTTP trigger. Microsoft's recommended approach.

```bicep
param teamsIntegrationType = 'workflow'
param teamsWorkflowUrl = 'https://prod-xx.westus.logic.azure.com:443/workflows/...'
```

**Setup:**
1. In Teams channel → Workflows → Create workflow
2. Add "When a HTTP request is received" trigger
3. Add "Post message in a chat or channel" action
4. Use the HTTP POST URL as `teamsWorkflowUrl`

### Option 4: Graph API (Advanced)
Microsoft Graph API with Teams app registration. Most flexible.

```bicep
param teamsIntegrationType = 'graph'
param teamsAppClientId = 'your-app-client-id'
param teamsAppClientSecret = 'your-app-secret'  # Use Key Vault!
param teamsChannelId = 'your-channel-id'
```

**Setup:**
1. Register app in Azure AD
2. Grant Microsoft Graph permissions: `ChannelMessage.Send`
3. Add app to Teams channel
4. Get channel ID from Teams

## Environment Variables

The deployment automatically configures these environment variables in the Web App:

### Core Services
- `AZ_DI_ENDPOINT` - Document Intelligence endpoint
- `AZ_DI_API_KEY` - Document Intelligence key (from Key Vault recommended)
- `SERVICE_BUS_CONNECTION_STRING` - Service Bus connection string
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - App Insights

### Teams Integration
- `TEAMS_INTEGRATION_TYPE` - none | webhook | workflow | graph
- `TEAMS_WEBHOOK_URL` - (if type=webhook)
- `TEAMS_WORKFLOW_URL` - (if type=workflow)
- `TEAMS_APP_CLIENT_ID` - (if type=graph)
- `TEAMS_APP_CLIENT_SECRET` - (if type=graph)
- `TEAMS_CHANNEL_ID` - (if type=graph)

### Application Config
- `APPROVAL_AMOUNT_THRESHOLD` - Auto-approval threshold (default: 500.0)
- `APPROVAL_MIN_CONFIDENCE` - Minimum confidence (default: 0.85)

## Resource Naming Convention

Resources follow this pattern: `{type}-adl-invoice-{env}-{location}`

Examples:
- `app-adl-invoice-dev-westus3` - Web App
- `di-adl-invoice-dev-westus3` - Document Intelligence
- `sb-adl-invoice-dev-westus3` - Service Bus

## Costs

### Development Environment
- App Service Plan (B1): ~$13/month
- Document Intelligence (F0): Free (limited transactions)
- Service Bus (Basic): ~$0.05/month
- **Total: ~$13/month**

### Production Environment
- App Service Plan (P1V2): ~$85/month
- Document Intelligence (S0): Pay-per-use (~$1.50/1K pages)
- Service Bus (Standard): ~$10/month + messages
- App Insights + Log Analytics: Pay-per-use (~$2/GB)
- **Total: ~$100-150/month + usage**

## Outputs

After deployment, the following outputs are available:

```bash
# Get deployment outputs
az deployment group show \
  --resource-group rg-adl-invoice-dev \
  --name main \
  --query properties.outputs
```

Key outputs:
- `webAppUrl` - Application URL
- `webAppName` - App name for code deployment
- `documentIntelligenceEndpoint` - DI endpoint
- `serviceBusNamespace` - Service Bus namespace

## Updating Infrastructure

To update existing infrastructure:

1. Modify Bicep templates or parameters
2. Run what-if to preview changes
3. Deploy with same command (idempotent)

```bash
# Preview
az deployment group what-if \
  --resource-group rg-adl-invoice-dev \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam

# Deploy
az deployment group create \
  --resource-group rg-adl-invoice-dev \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

## Secrets Management

**Best Practice:** Use Azure Key Vault for sensitive values:

```bicep
param teamsWebhookUrl string = '@Microsoft.KeyVault(SecretUri=https://kv-name.vault.azure.net/secrets/teams-webhook/)'
```

Or reference during deployment:

```bash
az deployment group create \
  --resource-group rg-adl-invoice-prod \
  --template-file main.bicep \
  --parameters parameters/prod.bicepparam \
  --parameters teamsWebhookUrl="$(az keyvault secret show --name teams-webhook --vault-name kv-name --query value -o tsv)"
```

## Troubleshooting

### Deployment fails with "Resource name already exists"
- Resource names must be globally unique (especially Document Intelligence)
- Modify `baseName` parameter or delete existing resources

### Document Intelligence quota exceeded
- Free tier (F0) limited to 500 pages/month
- Upgrade to S0 (Standard) for production

### App Service not starting
- Check Application Insights for errors
- Verify environment variables set correctly
- Check Deployment Center logs in Azure Portal

## Next Steps

After infrastructure deployment:

1. **Deploy application code**: Use GitHub Actions or Azure CLI
   ```bash
   az webapp deployment source config-zip \
     --resource-group rg-adl-invoice-dev \
     --name app-adl-invoice-dev-westus3 \
     --src <your-zip-file>
   ```

2. **Configure Teams integration**: Follow steps for chosen method above

3. **Test the system**: Upload invoice to test extraction/validation

4. **Set up monitoring**: Configure alerts in Application Insights

5. **Configure CI/CD**: Use `.github/workflows/deploy-infra.yml`