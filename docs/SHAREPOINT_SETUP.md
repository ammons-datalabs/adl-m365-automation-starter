# SharePoint + Logic Apps Setup Guide

This guide walks you through setting up the SharePoint library structure for the invoice automation workflow using Azure Logic Apps.

## Architecture

```
SharePoint "Invoices" Library
    ├── Incoming/        (drop invoices here)
    ├── Approved/        (AI auto-approved invoices)
    └── Pending/         (awaiting human review in Teams)
```

## Part 1: SharePoint Setup

### 1. Create Document Library

1. Go to your SharePoint site
2. Click **"+ New"** → **"Document library"**
3. Name: `Invoices`
4. Click **"Create"**

### 2. Create Folders

In the Invoices library, create three folders:
- Click **"+ New"** → **"Folder"**
- Create: `Incoming`, `Approved`, `Pending`

### 3. Add Custom Columns (Optional but Recommended)

Add these columns to track invoice metadata:

1. Click **Settings** (gear icon) → **Library settings**
2. Under "Columns", click **"Create column"** for each:
   - **Vendor** (Single line of text)
   - **InvoiceNumber** (Single line of text)
   - **InvoiceDate** (Date)
   - **Total** (Number, 2 decimals)
   - **Currency** (Single line of text)
   - **Confidence** (Number, 2 decimals)
   - **ApprovalType** (Choice: "AI Auto-Approved", "Human Approved", "Pending")
   - **ApprovalID** (Single line of text)

## Part 2: Azure Logic Apps Integration

Once your SharePoint library is configured, you can integrate it with Azure Logic Apps for automated invoice processing.

### Logic Apps Workflow

The Logic Apps workflow will:
1. **Trigger** when a file is created in SharePoint `/Invoices/Incoming/`
2. **Extract** invoice fields using FastAPI endpoints backed by Azure Document Intelligence
3. **Validate** against business rules (amount, confidence, document type, bill-to)
4. **Route** to `/Invoices/Approved/` or `/Invoices/Pending/` based on validation
5. **Update** SharePoint metadata (Status column)
6. **Send** Teams adaptive cards with approval details or failure reasons

### Setup Instructions

For detailed Logic Apps configuration, see [LOGIC_APPS_SETUP.md](LOGIC_APPS_SETUP.md).

You have two Logic App implementation options:
- **Modern approach**: `infra/logic-app-using-fastapi.json` (calls FastAPI `/extract` and `/validate` endpoints)
- **Legacy approach**: `infra/logic-app-definition.json` (calls Azure DI REST API directly)

We recommend the modern approach for better testability and reusable validation logic.

## Part 3: Testing

### Test 1: High Confidence Invoice (Should Auto-Approve)

1. Download sample invoice:
   ```bash
   curl -o test-invoice.pdf https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf
   ```

2. Upload to `Invoices/Incoming` folder

3. Expected:
   - Logic App triggers
   - API processes invoice (100% confidence)
   - File moves to `Approved`
   - Teams notification sent
   - Metadata updated

### Test 2: Low Confidence (Should Go to Teams)

For this, you need a lower-quality invoice. You can:
- Create a simple invoice in Word and save as PDF
- Use a photo of a handwritten receipt
- Adjust the threshold in the API call to force Teams routing

## Part 4: Monitoring

### View Logic App Runs

1. Go to Azure Portal
2. Navigate to your Logic App resource
3. Click **"Overview"** → **"Runs history"**
4. Click any run to see detailed execution logs
5. Review each step's inputs and outputs

### Common Issues

**Issue: Logic App fails at HTTP step**
- **Solution**: Check API URL is correct and Azure Web App is running
- Test health endpoint: `/health`

**Issue: "File not found" error**
- **Solution**: Ensure file is fully uploaded before Logic App triggers
- Add a 5-second delay after trigger if needed

**Issue: Timeout errors**
- **Solution**: Azure Document Intelligence can be slow. Increase timeout in HTTP action settings

## Part 5: Production Considerations

### Security
- Use Azure Key Vault for API credentials if needed
- Restrict SharePoint folder permissions
- Enable audit logging

### Performance
- Monitor Azure Application Insights
- Set up alerts for failures
- Consider batch processing for high volume

### Scaling
- Use parallel branches for multiple API calls
- Implement retry logic with exponential backoff
- Consider Azure Functions for complex workflows

## Next Steps

1. ✅ Set up SharePoint library and folders
2. ✅ Create and deploy Logic App (see [LOGIC_APPS_SETUP.md](LOGIC_APPS_SETUP.md))
3. ✅ Test with sample invoices
4. ✅ Configure Teams notifications
5. ✅ Set up monitoring and alerts
6. ✅ Train users on the system
7. ✅ Go live!

## Related Documentation

- **Logic Apps Setup**: [LOGIC_APPS_SETUP.md](LOGIC_APPS_SETUP.md) - Complete Logic App configuration guide
- **Integration Design**: [../INTEGRATION_DESIGN.md](../INTEGRATION_DESIGN.md) - System architecture and sequence diagrams
- **Main README**: [../README.md](../README.md) - Project overview and quickstart
