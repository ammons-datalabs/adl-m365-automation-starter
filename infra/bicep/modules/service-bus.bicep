// Service Bus module: Event-driven messaging
// Provides queue for invoice processing events

@description('Azure region for resources')
param location string

@description('Service Bus namespace name')
param serviceBusNamespaceName string

@description('Service Bus SKU')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string

@description('Tags to apply to resources')
param tags object

// ============================================================================
// SERVICE BUS NAMESPACE
// ============================================================================

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    minimumTlsVersion: '1.2'
  }
}

// ============================================================================
// INVOICE EVENTS QUEUE
// ============================================================================

resource invoiceEventsQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'invoice-events'
  properties: {
    maxSizeInMegabytes: 1024
    maxDeliveryCount: 10
    lockDuration: 'PT5M'  // 5 minutes
    defaultMessageTimeToLive: 'P14D'  // 14 days
    deadLetteringOnMessageExpiration: true
    enablePartitioning: false
    requiresDuplicateDetection: false
    requiresSession: false
  }
}

// ============================================================================
// AUTHORIZATION RULE (for connection string)
// ============================================================================

resource sendListenRule 'Microsoft.ServiceBus/namespaces/AuthorizationRules@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'SendListenRule'
  properties: {
    rights: [
      'Send'
      'Listen'
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Service Bus namespace name')
output namespaceName string = serviceBusNamespace.name

@description('Service Bus connection string')
output connectionString string = sendListenRule.listKeys().primaryConnectionString

@description('Invoice events queue name')
output queueName string = invoiceEventsQueue.name

@description('Service Bus namespace resource ID')
output namespaceId string = serviceBusNamespace.id