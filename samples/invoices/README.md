# Sample Invoices for Testing

This folder contains sample invoice PDFs for testing the invoice automation workflow.

## Quick Test (Docker + Web UI)

For rapid testing with Docker and the web UI at http://localhost:3000/upload:

**Setup:** Set authorized companies to `Ammons DataLabs` in the UI input field

**✅ Auto-Approve Test:** Use `simple-invoice-below-500.pdf`
- Bill To: Ammons DataLabs
- Expected: Green approval status, all checks pass
- Amount: ≤ $500, Confidence: > 85%, Type: Invoice

**❌ Manual Review Test:** Use `invoice-above-500.pdf`
- Expected: Amber pending status, amount check fails
- Amount: > $500 (exceeds threshold)

## Test Scenarios

### Auto-Approved Invoices (≤ $500, > 85% confidence)
These invoices should automatically route to the `/Invoices/Approved/` folder:
- Low-value invoices with clear, high-quality scans
- Total amount ≤ $500
- High OCR confidence (> 85%)
- Clearly labeled as "Invoice" (not "Receipt")

### Pending Review Invoices
These invoices should route to the `/Invoices/Pending/` folder for manual review:
- Invoices with total > $500
- Low confidence scans (≤ 85%)
- Poor quality or handwritten invoices
- Documents that might be receipts instead of invoices

## Testing the Workflow

1. **Upload to SharePoint:**
   - Navigate to your SharePoint site `/Invoices/Incoming/` folder
   - Drag and drop the sample PDFs

2. **Monitor the Logic App:**
   - Go to Azure Portal → Logic Apps → Your Logic App
   - Check "Run history" for execution details

3. **Verify Results:**
   - Check Teams channel for notifications
   - Verify files moved to Approved or Pending folders
   - Check SharePoint Status column is updated

4. **Expected Behavior:**
   - Auto-approved: Green checkmark notification in Teams, file in Approved folder
   - Pending: Yellow warning notification in Teams, file in Pending folder

## Sample Invoice Guidelines

When creating test invoices, include:
- Clear "INVOICE" header
- Vendor name and address
- Invoice number and date
- Line items with quantities and prices
- Subtotal, tax, and total amount
- Currency code (e.g., USD, AUD)

Avoid:
- Receipts (use "Receipt" header to test filtering)
- Handwritten or poorly scanned documents (test low confidence scenarios)
- Missing totals or unclear amounts

## Cleanup

After testing, you can safely delete invoices from Approved/Pending folders or move them back to Incoming to re-test.