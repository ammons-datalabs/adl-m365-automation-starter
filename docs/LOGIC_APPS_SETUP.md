# Logic Apps Setup Guide

This guide explains how to set up the intelligent invoice processing workflow using Azure Logic Apps, Azure Document Intelligence, SharePoint Online, and Microsoft Teams.

## Architecture Overview

![Logic App Flow](LogicAppFlow.png)

The workflow automatically:
1. Monitors a SharePoint library for new invoice PDFs
2. Extracts invoice data using Azure Document Intelligence
3. Evaluates approval criteria (amount ≤ $500, confidence > 85%, document type validation)
4. Routes invoices to "Approved" or "Pending" folders
5. Updates SharePoint metadata
6. Sends notifications to Microsoft Teams

## Prerequisites

### Azure Resources
- **Azure Logic App** (Consumption or Standard tier)
- **Azure Document Intelligence** resource
- **SharePoint Online** site with an "Invoices" document library
- **Microsoft Teams** channel with incoming webhook configured

### SharePoint Library Structure
```
Invoices/
├── Incoming/     # Drop new invoices here
├── Approved/     # Auto-approved invoices (≤$500, high confidence)
└── Pending/      # Manual review required
```

### SharePoint Columns
Add these columns to your Invoices library:
- **Status** (Choice): Approved, Pending, Rejected
- **Vendor** (Single line of text)
- **InvoiceTotal** (Currency) - optional
- **InvoiceDate** (Date) - optional

## Configuration

### 1. Azure Document Intelligence

Create a Document Intelligence resource in Azure:
```bash
az cognitiveservices account create \
  --name adl-invoice-extraction \
  --resource-group rg-adl-m365 \
  --kind FormRecognizer \
  --sku S0 \
  --location westus2
```

Get the endpoint and key:
```bash
az cognitiveservices account show \
  --name adl-invoice-extraction \
  --resource-group rg-adl-m365 \
  --query properties.endpoint

az cognitiveservices account keys list \
  --name adl-invoice-extraction \
  --resource-group rg-adl-m365
```

### 2. Teams Webhook

1. In Microsoft Teams, go to your channel
2. Click **...** → **Connectors** → **Incoming Webhook**
3. Name it "Invoice Notifications"
4. Copy the webhook URL

### 3. SharePoint Connection

1. In Azure Portal, go to Logic Apps Designer
2. Add a SharePoint Online connection
3. Sign in with your M365 account
4. Authorize access to your SharePoint site

## Logic App Workflow

### Step-by-Step Flow

#### 1. Trigger: When a file is created (properties only)
- **Site**: Your SharePoint site URL
- **Library**: Invoices
- **Folder**: /Invoices/Incoming
- **Frequency**: Every 1 minute

#### 2. Get file content
- **Site**: (same as trigger)
- **File Identifier**: `@triggerBody()?['{Identifier}']`

#### 3. HTTP POST: Analyze with Document Intelligence
```
URI: https://{your-endpoint}.cognitiveservices.azure.com/formrecognizer/documentModels/prebuilt-invoice:analyze?api-version=2023-07-31

Headers:
- Ocp-Apim-Subscription-Key: {your-key}
- Content-Type: application/pdf

Body:
@base64ToBinary(body('Get_file_content')?['$content'])
```

#### 4. Delay: 5 seconds
Wait for Document Intelligence to process the document.

#### 5. HTTP GET: Retrieve analysis results
```
URI: @outputs('HTTP')['headers']['Operation-Location']

Headers:
- Ocp-Apim-Subscription-Key: {your-key}
```

#### 6. Compose: Parse results
```
@body('HTTP_3')
```

#### 7. Condition: Evaluate approval criteria

**Expression:**
```javascript
@and(
  lessOrEquals(
    float(coalesce(outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceTotal']?['valueCurrency']?['amount'], 0)),
    500
  ),
  greater(
    float(coalesce(outputs('Compose')?['analyzeResult']?['documents']?[0]?['confidence'], 0)),
    0.85
  ),
  equals(
    contains(toLower(string(coalesce(outputs('Compose')?['analyzeResult']?['content'], ''))), 'invoice'),
    true
  ),
  equals(
    not(contains(toLower(string(coalesce(outputs('Compose')?['analyzeResult']?['content'], ''))), 'receipt')),
    true
  )
)
```

**Criteria:**
- Invoice total ≤ $500
- Document confidence > 85%
- Content contains "invoice"
- Content does NOT contain "receipt"

### If TRUE (Auto-Approve):

#### 8a. Update file properties
- **Status**: Approved
- **Vendor**: `@triggerBody()?['Vendor']`

#### 9a. Move file
- **Source File ID**: `@body('Update_file_properties')?['{Identifier}']`
- **Destination**: /Invoices/Approved

#### 10a. HTTP POST: Notify Teams
```json
{
  "text": "Auto-approved: @{triggerBody()?['Name']} | Total: $@{coalesce(outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceTotal']?['valueCurrency']?['amount'], 'n/a')}"
}
```

### If FALSE (Pending Review):

#### 8b. Update file properties
- **Status**: Pending
- **Vendor**: `@triggerBody()?['Vendor']`

#### 9b. Move file
- **Source File ID**: `@body('Update_file_properties_1')?['{Identifier}']`
- **Destination**: /Invoices/Pending

#### 10b. HTTP POST: Notify Teams
```json
{
  "text": "Pending approval: @{triggerBody()?['Name']} | Total: $@{coalesce(outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceTotal']?['valueCurrency']?['amount'], 'n/a')}"
}
```

## Deployment

### Option 1: Import from JSON

1. Create a new Logic App in Azure Portal
2. Go to "Logic app code view"
3. Paste the contents of `infra/logic-app-definition.json`
4. Update the following values:
   - SharePoint site URL
   - SharePoint library ID
   - Document Intelligence endpoint and key
   - Teams webhook URL
   - SharePoint connection ID

### Option 2: Manual Designer Setup

Follow the step-by-step flow above in the Logic Apps Designer.

## Key Expressions Reference

### Access extracted invoice fields
```javascript
// Invoice total amount
outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceTotal']?['valueCurrency']?['amount']

// Currency code
outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceTotal']?['valueCurrency']?['currencyCode']

// Vendor name
outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['VendorName']?['valueString']

// Invoice date
outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['InvoiceDate']?['valueDate']

// Document confidence
outputs('Compose')?['analyzeResult']?['documents']?[0]?['confidence']

// Line items
outputs('Compose')?['analyzeResult']?['documents']?[0]?['fields']?['Items']?['valueArray']
```

### Common Document Intelligence fields
- `AmountDue` - Total amount due
- `InvoiceTotal` - Invoice total
- `SubTotal` - Subtotal before tax
- `TotalTax` - Total tax amount
- `VendorName` - Vendor/supplier name
- `CustomerName` - Customer name
- `InvoiceId` - Invoice number
- `InvoiceDate` - Invoice date
- `Items` - Array of line items
- `TaxDetails` - Tax breakdown

## Testing

### Test the webhook
```bash
curl -X POST "https://metachunklabs.webhook.office.com/webhookb2/..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message: invoice-001.pdf | Total: $450.00"}'
```

### Test Document Intelligence endpoint
```bash
curl -X POST "https://adl-invoice-extraction.cognitiveservices.azure.com/formrecognizer/documentModels/prebuilt-invoice:analyze?api-version=2023-07-31" \
  -H "Ocp-Apim-Subscription-Key: {your-key}" \
  -H "Content-Type: application/pdf" \
  --data-binary "@sample-invoice.pdf"
```

### Upload a test invoice
1. Create a sample invoice PDF with a total < $500
2. Upload to SharePoint `/Invoices/Incoming/` folder
3. Wait 1-2 minutes for the Logic App to trigger
4. Check:
   - Logic App run history
   - Teams channel for notification
   - Invoice moved to Approved/Pending folder
   - SharePoint Status column updated

## Troubleshooting

### Common Issues

**404 Error on Document Intelligence**
- Verify endpoint URL format: `https://{name}.cognitiveservices.azure.com`
- Use stable API version: `2023-07-31` (not preview versions)
- Check that the API key is correct
- Path should be `/formrecognizer/documentModels/prebuilt-invoice:analyze`

**File not found when updating properties**
- Update properties BEFORE moving the file
- Use `@triggerBody()?['ID']` for the item ID (not the file path)

**Condition always evaluates to false**
- Check the expression syntax (use `float()` to convert values)
- Verify field paths in the Document Intelligence response
- Add `coalesce()` with default values to handle missing fields

**Teams notification not received**
- Test webhook URL with curl
- Check that JSON body is properly formatted
- Verify webhook hasn't been deleted from Teams

**SharePoint connection issues**
- Re-authorize the SharePoint connection
- Check that the service principal has access to the site
- Verify library ID is correct (found in the URL when viewing the library)

## Security Best Practices

### Secrets Management
**Do not commit secrets to the repository!** Use:
- Azure Key Vault for Document Intelligence keys
- Logic App managed identity for authentication
- Environment variables for webhook URLs

### Sample configuration (for reference only):
```bash
# DO NOT commit actual values
export DOCUMENT_INTELLIGENCE_ENDPOINT="https://adl-invoice-extraction.cognitiveservices.azure.com/"
export DOCUMENT_INTELLIGENCE_KEY="your-key-here"
export TEAMS_WEBHOOK_URL="https://metachunklabs.webhook.office.com/webhookb2/..."
export SHAREPOINT_SITE_URL="https://metachunklabs.sharepoint.com/sites/ADLInvoiceDemo"
```

## Next Steps

- [ ] Add Power BI dashboard for invoice analytics
- [ ] Implement manual approval workflow for pending invoices
- [ ] Add email notifications for high-value invoices
- [ ] Create custom Document Intelligence model for specific vendor formats
- [ ] Add exception handling and retry logic
- [ ] Integrate with ERP system (Dynamics 365, SAP, etc.)

## References

- [Azure Document Intelligence Documentation](https://learn.microsoft.com/azure/ai-services/document-intelligence/)
- [Logic Apps Workflow Definition Language](https://learn.microsoft.com/azure/logic-apps/logic-apps-workflow-definition-language)
- [SharePoint Online REST API](https://learn.microsoft.com/sharepoint/dev/sp-add-ins/get-to-know-the-sharepoint-rest-service)
- [Teams Incoming Webhooks](https://learn.microsoft.com/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
