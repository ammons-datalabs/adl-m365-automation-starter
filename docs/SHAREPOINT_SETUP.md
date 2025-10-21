# SharePoint + Power Automate Setup Guide

This guide walks you through setting up the complete invoice automation workflow on SharePoint.

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

## Part 2: Power Automate Flow

### Create the Flow

1. Go to https://make.powerautomate.com
2. Click **"+ Create"** → **"Automated cloud flow"**
3. Name: `Invoice Processing - Intelligent Routing`
4. Trigger: Search for **"When a file is created (properties only)"** (SharePoint)
5. Click **"Create"**

### Step-by-Step Flow Configuration

#### Step 1: Configure Trigger

**When a file is created (properties only)**
- **Site Address**: [Select your SharePoint site]
- **Library Name**: `Invoices`
- **Folder**: `/Incoming`
- **Include Nested Folders**: No

#### Step 2: Get File Content

Add action: **Get file content** (SharePoint)
- **Site Address**: [Same as trigger]
- **File Identifier**: `ID` (from dynamic content)

#### Step 3: Process Invoice with API

Add action: **HTTP**
- **Method**: `POST`
- **URI**:
  ```
  https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/invoices/process?confidence_threshold=0.85
  ```
- **Headers**: Leave empty (Power Automate will handle Content-Type)
- **Body**: Click "Show advanced options"
  - Select **"Body"** field
  - Add dynamic content: **File Content** (from "Get file content")

**Advanced Settings:**
- **Asynchronous Pattern**: On
- **Timeout**: `PT2M` (2 minutes - Azure DI can be slow)

**Important**: Power Automate will automatically handle the multipart/form-data encoding when you use the File Content directly in the body.

#### Step 4: Parse JSON Response

Add action: **Parse JSON** (Data Operation)
- **Content**: `Body` (from HTTP action)
- **Schema**: Click "Use sample payload to generate schema" and paste:
  ```json
  {
    "status": "auto_approved",
    "message": "Invoice auto-approved (confidence: 100%)",
    "approval_id": "abc-123",
    "invoice_data": {
      "vendor": "CONTOSO LTD.",
      "invoice_number": "INV-100",
      "invoice_date": "11/15/2019",
      "total": 110.0,
      "currency": "USD",
      "confidence": 1.0
    }
  }
  ```

#### Step 5: Condition - Check Status

Add action: **Condition** (Control)
- **Value**: `status` (from Parse JSON)
- **Operator**: `is equal to`
- **Value**: `auto_approved`

#### Step 6a: If Auto-Approved (Yes Branch)

**Action 1: Move file to Approved folder**
- Add action: **Move file** (SharePoint)
- **Site Address**: [Same as before]
- **Current File Identifier**: `ID` (from trigger)
- **Destination Folder Path**: `/Invoices/Approved`
- **Name if file exists**: `Add number suffix`

**Action 2: Update file properties**
- Add action: **Update file properties** (SharePoint)
- **Site Address**: [Same]
- **Library Name**: `Invoices`
- **Id**: `ID` (from "Move file" action - use the new ID)
- **Title**: `invoice_number` (from Parse JSON)
- Fill in custom columns:
  - **Vendor**: `vendor`
  - **InvoiceNumber**: `invoice_number`
  - **InvoiceDate**: `invoice_date`
  - **Total**: `total`
  - **Currency**: `currency`
  - **Confidence**: `confidence`
  - **ApprovalType**: `AI Auto-Approved`
  - **ApprovalID**: `approval_id`

**Action 3: Send Teams notification**
- Add action: **Post message in a chat or channel** (Teams)
- **Post as**: `Flow bot`
- **Post in**: `Channel`
- **Team**: [Your team]
- **Channel**: [Your channel]
- **Message**:
  ```
  ✅ Invoice Auto-Approved by AI

  Vendor: @{body('Parse_JSON')?['invoice_data']?['vendor']}
  Invoice #: @{body('Parse_JSON')?['invoice_data']?['invoice_number']}
  Total: @{body('Parse_JSON')?['invoice_data']?['currency']} @{body('Parse_JSON')?['invoice_data']?['total']}
  Confidence: @{mul(body('Parse_JSON')?['invoice_data']?['confidence'], 100)}%

  File: @{triggerOutputs()?['body/{FilenameWithExtension}']}
  Location: Invoices/Approved
  ```

#### Step 6b: If Pending Approval (No Branch)

**Action 1: Move file to Pending folder**
- Add action: **Move file** (SharePoint)
- **Site Address**: [Same]
- **Current File Identifier**: `ID` (from trigger)
- **Destination Folder Path**: `/Invoices/Pending`

**Action 2: Update file properties**
- Add action: **Update file properties** (SharePoint)
- [Same as above but **ApprovalType**: `Pending Human Review`]

**Action 3: Send Teams notification**
- Add action: **Post message in a chat or channel** (Teams)
- **Message**:
  ```
  📧 Invoice Requires Human Review

  Vendor: @{body('Parse_JSON')?['invoice_data']?['vendor']}
  Invoice #: @{body('Parse_JSON')?['invoice_data']?['invoice_number']}
  Total: @{body('Parse_JSON')?['invoice_data']?['currency']} @{body('Parse_JSON')?['invoice_data']?['total']}
  Confidence: @{mul(body('Parse_JSON')?['invoice_data']?['confidence'], 100)}% (below threshold)

  📋 An approval card has been sent to Teams.
  Check your Teams channel for the approval request.
  ```

### Step 7: Save and Test

1. Click **"Save"** (top right)
2. Name your flow if prompted
3. Click **"Test"** → **"Manually"**
4. Upload a test PDF to the `Invoices/Incoming` folder
5. Watch the flow run!

## Part 3: Testing

### Test 1: High Confidence Invoice (Should Auto-Approve)

1. Download sample invoice:
   ```bash
   curl -o test-invoice.pdf https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf
   ```

2. Upload to `Invoices/Incoming` folder

3. Expected:
   - Flow triggers
   - API processes (100% confidence)
   - File moves to `Approved`
   - Teams notification sent
   - Metadata updated

### Test 2: Low Confidence (Should Go to Teams)

For this, you need a lower-quality invoice. You can:
- Create a simple invoice in Word and save as PDF
- Use a photo of a handwritten receipt
- Adjust the threshold in the API call to force Teams routing

## Part 4: Monitoring

### View Flow Runs

1. Go to https://make.powerautomate.com
2. Click **"My flows"**
3. Click your flow
4. View **"28-day run history"**
5. Click any run to see detailed logs

### Common Issues

**Issue: Flow fails at HTTP step**
- **Solution**: Check API URL is correct and Azure app is running
- Test URL: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/health`

**Issue: "File not found" error**
- **Solution**: Ensure file is fully uploaded before flow triggers
- Add a 5-second delay after trigger

**Issue: Multipart encoding error**
- **Solution**: Make sure you're using File Content directly in HTTP body
- Power Automate handles encoding automatically

**Issue: Timeout after 120 seconds**
- **Solution**: Azure DI can be slow. Increase timeout or use async pattern

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
2. ✅ Create Power Automate flow
3. ✅ Test with sample invoices
4. ✅ Configure Teams notifications
5. ✅ Set up monitoring and alerts
6. ✅ Train users on the system
7. ✅ Go live!

## Support

- **API Health**: https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/health
- **View Approvals**: https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/invoices/approvals/approved
- **Documentation**: Review this repo's README and integration guides
