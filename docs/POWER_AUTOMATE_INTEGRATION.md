# Power Automate Integration Guide

This guide shows how to integrate the Invoice Automation API with Power Automate for end-to-end document processing workflows.

## Architecture

```
SharePoint Document Library
    ↓ (trigger: new file)
Power Automate Flow
    ↓ (HTTP POST with file)
Invoice Automation API (/invoices/process)
    ↓ (AI confidence check)
    ├─ High confidence → Auto-approve → ERP/Database
    └─ Low confidence → Teams approval → ERP/Database
```

## Prerequisites

- Power Automate license (included with Microsoft 365)
- SharePoint site with a document library
- Azure App Service URL: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net`

## Flow 1: Basic Invoice Processing

### Trigger
**When a file is created (properties only)** - SharePoint

### Actions

#### 1. Get file content
- **Action**: Get file content (SharePoint)
- **Site Address**: Your SharePoint site
- **File Identifier**: `ID` from trigger

#### 2. Process invoice with intelligent routing
- **Action**: HTTP
- **Method**: POST
- **URI**: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/invoices/process?confidence_threshold=0.85`
- **Headers**:
  ```
  Content-Type: multipart/form-data
  ```
- **Body**:
  ```
  --boundary
  Content-Disposition: form-data; name="file"; filename="@{triggerOutputs()?['body/{FilenameWithExtension}']}"
  Content-Type: application/pdf

  @{body('Get_file_content')}
  --boundary--
  ```

#### 3. Parse JSON response
- **Action**: Parse JSON
- **Content**: `@{body('HTTP')}`
- **Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "message": {"type": "string"},
      "approval_id": {"type": "string"},
      "invoice_data": {
        "type": "object",
        "properties": {
          "vendor": {"type": "string"},
          "invoice_number": {"type": "string"},
          "invoice_date": {"type": "string"},
          "total": {"type": "number"},
          "currency": {"type": "string"},
          "confidence": {"type": "number"}
        }
      }
    }
  }
  ```

#### 4. Condition: Check approval status
- **Condition**: `@{body('Parse_JSON')?['status']}` equals `auto_approved`

##### If auto-approved (Yes branch):
1. **Send notification**
   - Action: Post message in Teams/Send email
   - Message: "Invoice @{body('Parse_JSON')?['invoice_data']?['invoice_number']} auto-approved by AI"

2. **Write to database/ERP**
   - Action: Add row (SQL/Dataverse/Excel)
   - Vendor: `@{body('Parse_JSON')?['invoice_data']?['vendor']}`
   - Invoice #: `@{body('Parse_JSON')?['invoice_data']?['invoice_number']}`
   - Total: `@{body('Parse_JSON')?['invoice_data']?['total']}`
   - Approval Type: "AI Auto-Approved"

##### If pending approval (No branch):
1. **Log to Teams**
   - Action: Post message in Teams
   - Message: "Invoice @{body('Parse_JSON')?['invoice_data']?['invoice_number']} sent for human review"

2. **Optional: Create follow-up task**
   - Action: Create item (SharePoint Tasks/Planner)

## Flow 2: Advanced - Check Approval Status

This flow periodically checks for newly approved invoices and processes them.

### Trigger
**Recurrence** - Every 5 minutes

### Actions

#### 1. Get approved invoices
- **Action**: HTTP
- **Method**: GET
- **URI**: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/invoices/approvals/approved`

#### 2. Parse approved invoices
- **Action**: Parse JSON
- **Content**: `@{body('HTTP')}`
- **Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "total_approved": {"type": "integer"},
      "invoices": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "approval_id": {"type": "string"},
            "vendor": {"type": "string"},
            "invoice_number": {"type": "string"},
            "total": {"type": "number"},
            "currency": {"type": "string"},
            "confidence": {"type": "number"},
            "approval_type": {"type": "string"},
            "approved_by": {"type": "string"},
            "approved_at": {"type": "string"}
          }
        }
      }
    }
  }
  ```

#### 3. Apply to each approved invoice
- **Action**: Apply to each
- **Array**: `@{body('Parse_JSON')?['invoices']}`

Inside loop:
1. Check if already processed (query database by approval_id)
2. If not processed:
   - Write to ERP/Database
   - Send notification
   - Mark as processed

## Flow 3: Manual Approval Follow-up

Handle invoices that were sent to Teams for human review.

### Trigger
**When an HTTP request is received** (webhook from approval buttons)

Or use **Adaptive Card response** trigger if using Teams approval cards directly.

### Actions

1. Parse approval decision
2. Update database/ERP with approval status
3. Send confirmation notification

## PowerShell Alternative

For IT admins who prefer PowerShell automation:

```powershell
# Upload invoice and get intelligent routing
$apiUrl = "https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net"
$invoicePath = "C:\Invoices\invoice.pdf"

$fileContent = Get-Content $invoicePath -Raw -Encoding Byte
$boundary = [System.Guid]::NewGuid().ToString()

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"invoice.pdf`"",
    "Content-Type: application/pdf",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileContent),
    "--$boundary--"
)

$body = $bodyLines -join "`r`n"

$response = Invoke-RestMethod -Uri "$apiUrl/invoices/process?confidence_threshold=0.85" `
    -Method Post `
    -ContentType "multipart/form-data; boundary=$boundary" `
    -Body $body

Write-Host "Status: $($response.status)"
Write-Host "Vendor: $($response.invoice_data.vendor)"
Write-Host "Total: $($response.invoice_data.total)"
Write-Host "Confidence: $($response.invoice_data.confidence)"

if ($response.status -eq "auto_approved") {
    Write-Host "✅ Auto-approved by AI" -ForegroundColor Green
} else {
    Write-Host "📧 Sent to Teams for review" -ForegroundColor Yellow
}
```

## Best Practices

1. **Error Handling**: Add try-catch blocks in Power Automate to handle API errors
2. **Retry Logic**: Configure automatic retries for transient failures
3. **Logging**: Log all API calls to SharePoint list or Application Insights
4. **Security**: Use Azure Key Vault for storing API credentials if needed
5. **Monitoring**: Set up alerts for failed flows
6. **Testing**: Test with various invoice types and qualities

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/invoices/process` | POST | Smart processing with auto-routing |
| `/invoices/extract` | POST | Extract data only (no routing) |
| `/invoices/approvals/approved` | GET | List all approved invoices |
| `/invoices/approval/{id}/approve` | GET | Approve button handler |
| `/invoices/approval/{id}/reject` | GET | Reject button handler |
| `/health` | GET | Health check |

## Troubleshooting

### Issue: "The requested URL returned error: 400"
- **Cause**: Malformed multipart/form-data
- **Solution**: Ensure Content-Type header includes boundary parameter

### Issue: Invoices always going to Teams
- **Cause**: Confidence threshold too high
- **Solution**: Adjust threshold parameter (default: 0.85)

### Issue: "Could not resolve host"
- **Cause**: Azure App Service not accessible
- **Solution**: Verify the URL and check Azure App Service status

## Next Steps

1. Import sample flow from `samples/power-automate/`
2. Configure SharePoint connection
3. Test with sample invoices
4. Adjust confidence threshold based on your needs
5. Integrate with your ERP/accounting system
