// Document Intelligence module: Azure AI Document Intelligence
// Provides OCR and invoice field extraction capabilities

@description('Azure region for resources')
param location string

@description('Document Intelligence resource name')
param documentIntelligenceName string

@description('Document Intelligence SKU')
@allowed([
  'F0'  // Free tier
  'S0'  // Standard tier
])
param sku string

@description('Tags to apply to resources')
param tags object

// ============================================================================
// DOCUMENT INTELLIGENCE (FormRecognizer)
// ============================================================================

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: documentIntelligenceName
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: sku
  }
  properties: {
    customSubDomainName: documentIntelligenceName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Document Intelligence endpoint')
output endpoint string = documentIntelligence.properties.endpoint

@description('Document Intelligence primary key')
output key string = documentIntelligence.listKeys().key1

@description('Document Intelligence resource ID')
output resourceId string = documentIntelligence.id

@description('Document Intelligence name')
output name string = documentIntelligence.name