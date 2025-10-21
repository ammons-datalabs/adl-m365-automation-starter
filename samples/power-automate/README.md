# Power Automate Sample Flows

This directory contains sample Power Automate flows that can be imported and customized.

## Available Flows

### 1. `invoice-processing-basic.json`
Basic invoice processing flow that:
- Triggers when a new file is added to SharePoint
- Sends to invoice API for intelligent processing
- Routes based on AI confidence
- Logs results to SharePoint list

### 2. `invoice-batch-processor.json`
Scheduled batch processor that:
- Runs every hour
- Processes all invoices in a folder
- Moves processed files to archive
- Generates summary report

## How to Import

### Option 1: Import via Power Automate Portal
1. Go to https://make.powerautomate.com
2. Click "My flows" → "Import" → "Import Package (.zip)"
3. Upload the flow JSON file
4. Configure connections (SharePoint, HTTP)
5. Save and test

### Option 2: Create Manually
Since Power Automate doesn't support direct JSON import for all users, here's the manual setup:

#### Flow: Invoice Processing with Intelligent Routing

**Step 1: Add Trigger**
- Name: "When a file is created in SharePoint"
- Type: SharePoint trigger
- Configuration:
  - Site Address: [Your SharePoint site]
  - Library Name: "Invoices"

**Step 2: Get File Content**
- Name: "Get file content"
- Type: SharePoint action
- Configuration:
  - Site Address: [Same as trigger]
  - File Identifier: `ID` (from trigger dynamic content)

**Step 3: HTTP Request**
- Name: "Process Invoice with AI"
- Type: HTTP action
- Configuration:
  - Method: `POST`
  - URI: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net/invoices/process?confidence_threshold=0.85`
  - Headers:
    ```
    Content-Type: multipart/form-data; boundary=----boundary
    ```
  - Body: See Power Automate Integration Guide for multipart body format

**Step 4: Parse JSON**
- Name: "Parse API Response"
- Type: Data Operation - Parse JSON
- Content: Body from HTTP action
- Schema: See integration guide

**Step 5: Condition**
- Name: "Check if Auto-Approved"
- Condition: `status` equals `auto_approved`

**Step 6a: If Yes (Auto-Approved)**
- Add row to Excel/SharePoint/SQL
- Send Teams notification
- Move file to "Approved" folder

**Step 6b: If No (Pending Approval)**
- Log to SharePoint list
- Send Teams notification for manual review

## Configuration Variables

Before using these flows, update these values:

- `SHAREPOINT_SITE`: Your SharePoint site URL
- `API_BASE_URL`: `https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net`
- `CONFIDENCE_THRESHOLD`: Default 0.85 (adjust based on your needs)
- `TEAMS_CHANNEL`: Channel ID for notifications

## Testing

1. Upload a sample invoice to your SharePoint library
2. Monitor flow run history
3. Check for success/failure
4. Verify data in destination (database/Excel/etc.)

## Troubleshooting

**Common Issues:**

1. **401 Unauthorized**
   - Solution: Check API authentication settings

2. **Multipart form-data errors**
   - Solution: Use the exact boundary format shown in the integration guide

3. **Flow times out**
   - Solution: Azure DI can take 10-30 seconds; set HTTP timeout to 60 seconds

## Advanced: PowerShell Script

For bulk processing or scheduled tasks outside Power Automate:

```powershell
# See docs/POWER_AUTOMATE_INTEGRATION.md for full PowerShell script
```

## Support

For issues or questions:
- Review logs in Azure Application Insights
- Check Power Automate flow run history
- Test API endpoints directly with Postman/curl
